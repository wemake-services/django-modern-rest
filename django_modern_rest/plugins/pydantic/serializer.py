from collections.abc import Callable, Mapping
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    Union,
    final,
)

import pydantic
import pydantic_core
from pydantic.config import ExtraValues
from typing_extensions import TypedDict, override

from django_modern_rest.envs import MAX_CACHE_SIZE
from django_modern_rest.errors import ErrorDetail, ErrorType
from django_modern_rest.exceptions import InternalServerError
from django_modern_rest.parsers import Parser, Raw
from django_modern_rest.renderers import Renderer
from django_modern_rest.serializer import (
    BaseEndpointOptimizer,
    BaseSerializer,
)

if TYPE_CHECKING:
    from django_modern_rest.metadata import EndpointMetadata


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
        for response in metadata.responses.values():
            _get_cached_type_adapter(response.return_type)


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
    deserialize_strict: ClassVar[bool] = True

    @override
    @classmethod
    def serialize(
        cls,
        structure: Any,
        *,
        renderer_cls: type[Renderer],
    ) -> bytes:
        """Convert any object to raw bytestring."""
        try:
            return renderer_cls.render(
                structure,
                cls.serialize_hook,
            )
        except pydantic_core.PydanticSerializationError as exc:
            raise InternalServerError(str(exc)) from None

    @override
    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """Customize how some objects are serialized into simple objects."""
        if isinstance(to_serialize, pydantic.BaseModel):
            return to_serialize.model_dump(**cls.model_dump_kwargs)
        return super().serialize_hook(to_serialize)

    @override
    @classmethod
    def deserialize(
        cls,
        buffer: Raw,
        *,
        parser_cls: type[Parser],
    ) -> Any:
        """Convert string or bytestring to simple python object."""
        return parser_cls.parse(
            buffer,
            cls.deserialize_hook,
            strict=cls.deserialize_strict,
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
        # At this point `_get_cached_type_adapter(model)` was already called
        # during the optimizer stage, so it will be very fast to use in runtime.
        return _get_cached_type_adapter(model).validate_python(
            unstructured,
            strict=strict or None,
            **cls.from_python_kwargs,
        )

    @override
    @classmethod
    def serialize_validation_error(
        cls,
        exc: Exception,
    ) -> list[ErrorDetail]:
        """Serialize validation error."""
        if isinstance(exc, pydantic.ValidationError):
            return [
                {
                    'msg': error['msg'],
                    'loc': [str(loc) for loc in error['loc']],
                    'type': str(ErrorType.value_error),
                }
                for error in exc.errors(
                    include_url=False,
                    include_context=False,
                    include_input=False,
                )
            ]
        raise NotImplementedError(
            f'Cannot serialize exception {exc!r} of type {type(exc)} safely',
        )


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _get_cached_type_adapter(model: Any) -> pydantic.TypeAdapter[Any]:
    """
    It is expensive to create, reuse existing ones.

    If you want to clear this cache run:

    .. code:: python

        >>> _get_cached_type_adapter.cache_clear()

    Or use :func:`django_modern_rest.settings.clear_settings_cache`.
    """
    # This is a function not to cache `self` or `cls`
    return pydantic.TypeAdapter(model)
