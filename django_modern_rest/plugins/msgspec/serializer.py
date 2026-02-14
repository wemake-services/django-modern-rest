from collections.abc import Iterable
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NotRequired,
)

import msgspec
from django.http import HttpRequest
from typing_extensions import TypedDict, override

from django_modern_rest.errors import ErrorDetail, ErrorType
from django_modern_rest.parsers import Parser, Raw
from django_modern_rest.renderers import Renderer
from django_modern_rest.serializer import (
    BaseEndpointOptimizer,
    BaseSerializer,
)

if TYPE_CHECKING:
    from django_modern_rest.metadata import EndpointMetadata


class MsgspecConvertOptions(TypedDict):
    """Custom serializer API options, taken by `msgpec.convert`."""

    from_attributes: NotRequired[bool]
    builtin_types: NotRequired[Iterable[type] | None]
    str_keys: NotRequired[bool]


class MsgspecEndpointOptimizer(BaseEndpointOptimizer):
    """Optimize endpoints that are parsed with Msgspec."""

    @override
    @classmethod
    def optimize_endpoint(cls, metadata: 'EndpointMetadata') -> None:
        """Does nothing for msgspec."""
        # `msgspec.convert` does not have any API
        # to pre-build validation schema.
        # Returning `Struct` or `list[Struct]` will be just fast enough.


class MsgspecSerializer(BaseSerializer):
    """
    Serialize and deserialize objects using msgspec.

    Msgspec support is optional.
    To install it run:

    .. code:: bash

        pip install 'django-modern-rest[msgspec]'

    """

    __slots__ = ()

    # Required API:
    validation_error: ClassVar[type[Exception]] = msgspec.ValidationError
    optimizer: ClassVar[type[BaseEndpointOptimizer]] = MsgspecEndpointOptimizer

    # Custom API:
    convert_kwargs: ClassVar[MsgspecConvertOptions] = {}

    @override
    @classmethod
    def serialize(
        cls,
        structure: Any,
        *,
        renderer: Renderer,
    ) -> bytes:
        """Convert any object to a raw bytestring."""
        return renderer.render(structure, cls.serialize_hook)

    @override
    @classmethod
    def deserialize(
        cls,
        buffer: Raw,
        *,
        parser: Parser,
        request: HttpRequest,
    ) -> Any:
        """Convert string or bytestring to simple python object."""
        return parser.parse(
            buffer,
            cls.deserialize_hook,
            request=request,
        )

    @override
    @classmethod
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
        *,
        strict: bool | None,
    ) -> Any:
        """
        Parse *unstructured* data from python primitives into *model*.

        Args:
            unstructured: Python objects to be parsed / validated.
            model: Python type to serve as a model.
                Can be any type that ``msgspec`` supports.
                Examples: ``dict[str, int]`` and ``BaseModel`` subtypes.
            strict: Whether we use more strict validation rules.
                For example, it is fine for a request validation
                to be less strict in some cases and allow type coercition.
                But, response types need to be strongly validated.

        Raises:
            msgspec.ValidationError: When parsing can't be done.

        Returns:
            Structured and validated data.
        """
        return msgspec.convert(
            unstructured,
            model,
            strict=strict or False,
            dec_hook=cls.deserialize_hook,
            **cls.convert_kwargs,
        )

    @override
    @classmethod
    def serialize_validation_error(
        cls,
        exc: Exception,
    ) -> list[ErrorDetail]:
        """Serialize validation error."""
        if isinstance(exc, msgspec.ValidationError):
            return [{'msg': str(exc), 'type': str(ErrorType.value_error)}]
        raise NotImplementedError(
            f'Cannot serialize exception {exc!r} of type {type(exc)} safely',
        )
