from collections.abc import Callable, Mapping
from dataclasses import is_dataclass
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    TypeVar,
    Union,
    final,
)

import pydantic
import pydantic_core
from django.http import HttpRequest
from pydantic.config import ExtraValues
from typing_extensions import TypedDict, override

from dmr.envs import MAX_CACHE_SIZE
from dmr.errors import ErrorDetail, ErrorType
from dmr.exceptions import DataParsingError, DataRenderingError
from dmr.parsers import Parser, Raw
from dmr.plugins.pydantic.schema import PydanticSchemaGenerator
from dmr.renderers import Renderer
from dmr.serializer import BaseEndpointOptimizer, BaseSerializer

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata


# pydantic does not allow to import this,
# so we have to duplicate this type.
_IncEx: TypeAlias = (
    set[int]
    | set[str]
    | Mapping[int, Union['_IncEx', bool]]
    | Mapping[str, Union['_IncEx', bool]]
)


@final
class ToJsonKwargs(TypedDict, total=False):
    """Keyword arguments for pydantic's model dump method."""

    # `mode` is explicitly left out. It is always `json`.
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
class ToModelKwargs(TypedDict, total=False):
    """Keyword arguments for pydantic's python object validation method."""

    # `from_attributes` is explicitly left out. It is always `False`.
    extra: ExtraValues | None
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
        # Just build all `TypeAdapter` instances
        # during import time and cache them for later use in runtime.
        for response in metadata.responses.values():
            _get_cached_type_adapter(response.return_type)
        # It is used in many places:
        _get_cached_type_adapter(Any)


class PydanticSerializer(BaseSerializer):
    """
    Serialize and deserialize objects using pydantic.

    Pydantic support is optional.
    To install it run:

    .. code:: bash

        pip install 'django-modern-rest[pydantic]'

    Attributes:
        to_json_kwargs: Dictionary of kwargs that will be passed
            to model serialization callbacks.
        to_model_kwargs: Dictionary of kwargs that will be passed
            to model deserialization callbacks.

    """

    __slots__ = ()

    # Required API:
    validation_error = pydantic_core.ValidationError
    optimizer = PydanticEndpointOptimizer
    schema_generator = PydanticSchemaGenerator

    # Custom API:
    to_json_kwargs: ClassVar[ToJsonKwargs] = {
        'by_alias': True,
    }

    to_model_kwargs: ClassVar[ToModelKwargs] = {
        'by_alias': True,
    }

    @override
    @classmethod
    def serialize(
        cls,
        structure: Any,
        *,
        renderer: Renderer,
    ) -> bytes:
        """Convert any object to raw bytestring."""
        try:
            return renderer.render(
                structure,
                cls.serialize_hook,
            )
        except pydantic_core.PydanticSerializationError as exc:
            raise DataRenderingError(str(exc)) from None

    @override
    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """Customize how some objects are serialized into simple objects."""
        if isinstance(to_serialize, pydantic.BaseModel):
            return to_serialize.model_dump(mode='json', **cls.to_json_kwargs)
        # We support dataclasses here, because raw `JsonRenderer`
        # does not support them, however, we use them in multiple places inside:
        if is_dataclass(to_serialize):
            return _get_cached_type_adapter(
                type(to_serialize),  # type: ignore[arg-type]
            ).dump_python(
                to_serialize,
            )
        # This is a pydantic field inside a `TypedDict`, `@dataclass`, etc:
        if hasattr(to_serialize, '__get_pydantic_core_schema__'):
            return _get_cached_type_adapter(
                type(to_serialize),  # type: ignore[arg-type]
            ).dump_python(to_serialize, mode='json', **cls.to_json_kwargs)
        return super().serialize_hook(to_serialize)

    @override
    @classmethod
    def deserialize(
        cls,
        buffer: Raw,
        *,
        parser: Parser,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        """Convert string or bytestring to simple python object."""
        return parser.parse(
            buffer,
            cls.deserialize_hook,
            request=request,
            model=model,
        )

    @override
    @classmethod
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
        *,
        strict: bool | None,
        rebuild_namespace: Mapping[str, Any] | None = None,
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
            rebuild_namespace: Optional namespace to rebuild the type adapter.
                Should be used when there are forward references
                that pydantic cannot solve by itself.

        Returns:
            Structured and validated data.

        Raises:
            pydantic_core.ValidationError: When parsing can't be done.

        """
        # At this point `_get_cached_type_adapter(model)` was already called
        # during the optimizer stage, so it will be very fast to use in runtime.
        adapter = _get_cached_type_adapter(model)
        if rebuild_namespace is not None:
            adapter.rebuild(_types_namespace=rebuild_namespace)
        return adapter.validate_python(
            unstructured,
            strict=strict,
            **cls.to_model_kwargs,
        )

    @override
    @classmethod
    def to_python(
        cls,
        structured: Any,
    ) -> Any:
        """
        Unparse *structured* data from a model into Python primitives.

        Args:
            structured: Model instance.

        Returns:
            Unstructured data.

        """
        return _get_cached_type_adapter(Any).dump_python(
            structured,
            mode='json',
            **cls.to_json_kwargs,
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


class PydanticFastSerializer(PydanticSerializer):
    """
    Fast pydantic serializer for cases when you only work with json.

    Does not use ``parser`` and ``renderer`` passed objects, does not use
    ``dmr.plugins.pyndatic.PydanticSerializer.serialize_hook`` and
    ``dmr.plugins.pyndatic.PydanticSerializer.deserialize_hook``
    method.

    Is built for optimizations only, use with caution.

    Only works with ``application/json`` content type.

    .. versionadded:: 0.6.0

        See :issue:`830`.

    """

    @classmethod
    @override
    def serialize(cls, structure: Any, *, renderer: Renderer) -> bytes:
        """
        Fast way to serializer pyndatic models into json bytestring.

        *renderer* parameter is always ignored.
        """
        try:
            return _get_cached_type_adapter(Any).dump_json(
                structure,
                fallback=cls.serialize_hook,
                **cls.to_json_kwargs,  # type: ignore[misc]
            )
        except pydantic_core.PydanticSerializationError as exc:
            raise DataRenderingError(str(exc)) from exc

    @classmethod
    @override
    def deserialize(
        cls,
        buffer: Raw,
        *,
        parser: Parser,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        """
        Fast way to serializer pyndatic models into json bytestring.

        *parser* parameter is always ignored.
        """
        try:
            return _get_cached_type_adapter(Any).validate_json(
                buffer,
                **cls.to_model_kwargs,
            )
        except pydantic_core.ValidationError as exc:
            raise DataParsingError(exc.errors()[0]['msg']) from exc

    @classmethod
    @override
    def is_supported(cls, pluggable: Parser | Renderer) -> bool:
        """
        Is this parser or renderer supported?

        We only support ``json`` parsers and renderers.
        """
        return pluggable.content_type == 'application/json'


_ModelT = TypeVar('_ModelT')


@lru_cache(maxsize=MAX_CACHE_SIZE)
def _get_cached_type_adapter(model: _ModelT) -> pydantic.TypeAdapter[_ModelT]:
    """
    It is expensive to create, reuse existing ones.

    If you want to clear this cache run:

    .. code:: python

        >>> _get_cached_type_adapter.cache_clear()

    Or use :func:`dmr.settings.clear_settings_cache`.
    """
    # This is a function not to cache `self` or `cls` params.
    return pydantic.TypeAdapter(model, _parent_depth=4)
