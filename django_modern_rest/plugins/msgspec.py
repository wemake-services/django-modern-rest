from collections.abc import Iterable
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    NotRequired,
)

try:
    import msgspec
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `msgspec` is not installed, '
        "consider using `pip install 'django-modern-rest[msgspec]'`",
    )
    raise


from typing_extensions import TypedDict, override

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
    from django_modern_rest.internal.json import (
        FromJson,
    )
    from django_modern_rest.metadata import EndpointMetadata


class MsgspecErrorDetails(TypedDict):
    """Base schema for msgspec error detail."""

    type: str
    loc: list[int | str]
    msg: str


class MsgspecConvertOptions(TypedDict):
    """Custom serializer API options, taken by `msgpec.convert`."""

    from_attributes: NotRequired[bool]
    builtin_types: NotRequired[Iterable[type] | None]
    str_keys: NotRequired[bool]


class MsgspecErrorModel(TypedDict):
    """Error response schema for serialization errors."""

    detail: list[MsgspecErrorDetails]


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
    response_parsing_error_model: ClassVar[Any] = MsgspecErrorModel

    # Custom API:
    from_json_strict: ClassVar[bool] = True
    convert_kwargs: ClassVar[MsgspecConvertOptions] = {}

    @override
    @classmethod
    def serialize(cls, structure: Any) -> bytes:
        """Convert any object to json bytestring."""
        serialize = resolve_setting(DMR_SERIALIZE_KEY, import_string=True)
        return serialize(  # type: ignore[no-any-return]
            structure,
            cls.serialize_hook,
        )

    @override
    @classmethod
    def deserialize(cls, buffer: 'FromJson') -> Any:
        """
        Convert string or bytestring to simple python object.

        TypeAdapter used for type validation is cached for further uses.
        """
        deserialize = resolve_setting(DMR_DESERIALIZE_KEY, import_string=True)
        return deserialize(
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
            strict=strict,
            dec_hook=cls.deserialize_hook,
            **cls.convert_kwargs,
        )

    @override
    @classmethod
    def error_serialize(
        cls,
        error: Exception | str,
    ) -> list[MsgspecErrorDetails]:
        """
        Serialize a serializer exception to json the best way possible.

        Args:
            error: A serialization exception like a validation error or
                a ``django_modern_rest.exceptions.DataParsingError``.

        Returns:
            Simple python object - exception converted to json.
        """
        if isinstance(error, msgspec.ValidationError):
            return [{'type': 'value_error', 'loc': [], 'msg': str(error)}]
        raise NotImplementedError(
            f'Cannot serialize {error!r} of type {type(error)} to json safely',
        )
