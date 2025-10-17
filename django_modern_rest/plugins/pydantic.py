from collections.abc import Callable, Mapping
from functools import cache
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    TypedDict,
    Union,
    final,
)

try:
    import pydantic
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pydantic` is not installed, '
        "consider using `pip install 'django-modern-rest[pydantic]'`",
    )
    raise

import pydantic_core
from django.utils.module_loading import import_string
from pydantic.config import ExtraValues
from typing_extensions import override

from django_modern_rest.exceptions import ResponseSerializationError
from django_modern_rest.serialization import (
    BaseEndpointOptimizer,
    BaseSerializer,
)
from django_modern_rest.settings import (
    DMR_DESERIALIZE_KEY,
    DMR_SERIALIZE_KEY,
    resolve_setting,
)

if TYPE_CHECKING:
    from django_modern_rest.endpoint import EndpointMetadata
    from django_modern_rest.internal.json import (
        Deserialize,
        FromJson,
        Serialize,
    )


# pydantic does not allow to import this,
# so we have to duplicate this type.
_IncEx: TypeAlias = (
    set[int]
    | set[str]
    | Mapping[int, Union['_IncEx', bool]]
    | Mapping[str, Union['_IncEx', bool]]
)


@final
class ModelDumpKwargs(TypedDict, total=False):
    """Keyword arguments for pydantic's model dump method."""

    mode: Literal['json', 'python'] | str
    include: _IncEx | None
    exclude: _IncEx | None
    context: Any | None
    by_alias: bool | None
    exclude_unset: bool
    exclude_defaults: bool
    exclude_none: bool
    exclude_computed_fields: bool
    round_trip: bool
    warnings: bool | Literal['none', 'warn', 'error']
    fallback: Callable[[Any], Any] | None
    serialize_as_any: bool


@final
class FromPythonKwargs(TypedDict, total=False):
    """Keyword arguments for pydantic's python object validation method."""

    extra: ExtraValues | None
    from_attributes: bool | None
    context: Any | None
    experimental_allow_partial: bool | Literal['off', 'on', 'trailing-strings']
    by_alias: bool | None
    by_name: bool | None


class PydanticEndpointOptimizer(BaseEndpointOptimizer):
    """Optimize endpoints that are parsed with pydantic."""

    @override
    @classmethod
    def optimize_endpoint(cls, metadata: 'EndpointMetadata') -> None:
        """Create models for return types for validation."""
        # Just build all `TypeAdapater` instances
        # during import time and cache them for later use in runtime.
        _get_cached_type_adapter(metadata.return_type)


class PydanticSerializer(BaseSerializer):
    """
    Serialize and deserialize objects using pydantic.

    Pydantic support is optional.
    To install it run:

    .. code:: bash

        pip install 'django-modern-rest[pydantic]'

    """

    __slots__ = ()

    # Required API:
    validation_error: ClassVar[type[Exception]] = pydantic.ValidationError
    optimizer: ClassVar[type[BaseEndpointOptimizer]] = PydanticEndpointOptimizer

    # Custom API:

    model_dump_kwargs: ClassVar[ModelDumpKwargs] = {
        'by_alias': True,
        'mode': 'json',
    }
    from_python_kwargs: ClassVar[FromPythonKwargs] = {
        'by_alias': True,
    }
    from_json_strict: ClassVar[bool] = True

    # Private API:

    _serialize: ClassVar['Serialize']
    _deserialize: ClassVar['Deserialize']

    @override
    @classmethod
    def to_json(cls, structure: Any) -> bytes:
        """Convert any object to json bytestring."""
        try:
            return _get_serialize_func(cls)(structure, cls.serialize_hook)
        except pydantic_core.PydanticSerializationError as exc:
            raise ResponseSerializationError(str(exc)) from None

    @override
    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """Customize how some objects are serialized into json."""
        if isinstance(to_serialize, pydantic.BaseModel):
            return to_serialize.model_dump(**cls.model_dump_kwargs)
        return super().serialize_hook(to_serialize)

    @override
    @classmethod
    def from_json(cls, buffer: 'FromJson') -> Any:
        """
        Convert string or bytestring to simple python object.

        TypeAdapter used for type validation is cached for futher uses.
        """
        return _get_deserialize_func(cls)(
            buffer,
            cls.deserialize_hook,
            strict=cls.from_json_strict,
        )

    @override
    @classmethod
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
        *,
        strict: bool,
    ) -> Any:
        """
        Parse *unstructured* data from python primitives into *model*.

        Args:
            unstructured: Python objects to be parsed / validated.
            model: Python type to serve as a model.
                Can be any type that ``pydantic`` supports.
                Examples: ``dict[str, int]`` and ``BaseModel`` subtypes.
            strict: Whether we use more strict validation rules.
                For example, it is fine for a request validation
                to be less strict in some cases and allow type coercition.
                But, response types need to be strongly validated.

        Raises:
            pydantic.ValidationError: When parsing can't be done.

        Returns:
            Structured and validated data.
        """
        # TODO: support `.rebuild` and forward refs
        # TODO: handle PydanticSchemaGenerationError here
        # TODO: call `_get_cached_type_adapter(model)` on import time
        # the first time, so first requests won't be affected in runtime.
        return _get_cached_type_adapter(model).validate_python(
            unstructured,
            strict=strict,
            **cls.from_python_kwargs,
        )

    @override
    @classmethod
    def error_to_json(cls, error: Exception) -> list[Any]:
        """Serialize an exception to json the best way possible."""
        # Security notice: we only process custom exceptions
        # with this functions, so nothing should leak from exc messages.
        assert isinstance(error, pydantic.ValidationError), (  # noqa: S101
            f'Cannot serialize {error} to json safely'
        )
        return error.errors(include_url=False)


# TODO: merge `_get_serialize_func` and `_get_deserialize_func`?
def _get_serialize_func(cls: type[PydanticSerializer]) -> 'Serialize':
    existing_attr: Serialize | None = getattr(cls, '_serialize', None)
    if existing_attr is not None:
        return existing_attr

    setting = resolve_setting(DMR_SERIALIZE_KEY)
    cls._serialize = (  # pyright: ignore[reportPrivateUsage]
        import_string(setting) if isinstance(setting, str) else setting
    )
    return cls._serialize  # pyright: ignore[reportPrivateUsage]


def _get_deserialize_func(cls: type[PydanticSerializer]) -> 'Deserialize':
    existing_attr: Deserialize | None = getattr(cls, '_deserialize', None)
    if existing_attr is not None:
        return existing_attr

    setting = resolve_setting(DMR_DESERIALIZE_KEY)
    cls._deserialize = (  # pyright: ignore[reportPrivateUsage]
        import_string(setting) if isinstance(setting, str) else setting
    )
    return cls._deserialize  # pyright: ignore[reportPrivateUsage]


@cache
def _get_cached_type_adapter(model: Any) -> pydantic.TypeAdapter[Any]:
    """
    It is expensive to create, reuse existing ones.

    If you want to clear this cache run:

    .. code:: python

        >>> _get_cached_type_adapter.cache_clear()

    """
    # This is a function not to cache `self` or `cls`
    return pydantic.TypeAdapter(model)
