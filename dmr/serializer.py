import abc
import dataclasses
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Final, TypeAlias, final

from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from dmr.errors import ErrorDetail
from dmr.exceptions import DataRenderingError, RequestSerializationError
from dmr.internal.types import EMPTY
from dmr.parsers import Parser, Raw
from dmr.renderers import Renderer

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata

_CANNOT_DESERIALIZE_MSG: Final = _(
    'Value {value} of type {type} is not supported for {target_type}',
)

SchemaDef: TypeAlias = tuple[
    dict[str, Any],
    dict[str, Any],
]


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ContextField:
    """
    Single field of a context model to be built by a serializer.

    .. versionadded:: 0.16.0
    """

    annotation: Any
    """Type annotation to parse the field into."""

    default: Any = EMPTY
    """
    Default value of the field, used when the field is missing.

    :data:`~dmr.types.EMPTY` means that the field is required.
    It is always the exact object that the endpoint has as its default,
    we never copy it or wrap it into any factories.
    """


def context_field_tuples(
    fields: Mapping[str, ContextField],
) -> list[tuple[Any, ...]]:
    """
    Convert context fields into tuples that model constructors accept.

    Both :func:`dataclasses.make_dataclass` and :func:`msgspec.defstruct`
    accept ``(name, type)`` tuples for required fields
    and ``(name, type, default)`` tuples for fields with defaults.
    Fields with defaults always go after the fields without them,
    just like in regular function signatures.

    .. versionadded:: 0.16.0
    """
    required = [
        (field_name, field.annotation)
        for field_name, field in fields.items()
        if field.default is EMPTY
    ]
    with_defaults = [
        (field_name, field.annotation, field.default)
        for field_name, field in fields.items()
        if field.default is not EMPTY
    ]
    return [*required, *with_defaults]


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ContextModel:
    """
    Model that a serializer has built to parse the whole request context.

    .. versionadded:: 0.16.0
    """

    model: Any
    """Any type that :meth:`BaseSerializer.from_python` can parse into."""

    to_kwargs: Callable[[Any], dict[str, Any]] | None = None
    """
    Converts a parsed model instance into a mapping of field names to values.

    ``None`` means that :meth:`BaseSerializer.from_python` already returns
    a mapping for this model, so no conversion is needed.
    """


class BaseEndpointOptimizer:
    """
    Plugins might often need to run some specific preparations for endpoints.

    To achieve that we provide an explicit API for that.
    """

    __slots__ = ()

    @classmethod
    @abc.abstractmethod
    def optimize_endpoint(cls, metadata: 'EndpointMetadata') -> None:
        """
        Optimize the endpoint.

        Args:
            metadata: Endpoint metadata to optimize.

        """
        raise NotImplementedError


class BaseSchemaGenerator:
    """Generates JSON schema by the native serializer API."""

    __slots__ = ()

    @classmethod
    @abc.abstractmethod
    def get_schema(
        cls,
        model: Any,
        ref_template: str,
        *,
        used_for_response: bool = False,
    ) -> SchemaDef:
        """
        Provide JSON schema / OpenAPI spec for the given model.

        Args:
            model: Model to generate JSON schema for.
            ref_template: Reference template to use for the references.
            used_for_response: Is this schema used for the response or request.

        Raises:
            Exception: when schema cannot be built.
                Can be any :exc:`Exception` subclass instance.

        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def schema_name(cls, model: Any) -> str | None:
        """
        Return a schema name for a model, if it exists.

        It is done directly by the serializer,
        we don't store any specific logic for it.
        """
        raise NotImplementedError


class BaseSerializer:  # noqa: WPS214
    """
    Abstract base class for data serialization.

    What serializer does?

    1. It provides serialization and deserialization hooks
       for parser and renderer. So different parsers and renderers
       will work similarly. This way you can modify all the serialization
       logic in one place and not adjust all possible parsers or renderers
    2. It provides validation for raw python data,
       see :meth:`dmr.serializer.BaseSerializer.from_python` method
    3. It provides serialization for related complex utility objects like
       validation errors and responses that don't have ``.content`` attribute.
       For example: file and sse responses

    Attributes:
        validation_error: Exception type that is used for validation errors.
            Required to be set in subclasses.
        optimizer: Endpoint optimizer.
            Type that pre-compiles / creates / caches models in import time.
            Required to be set in subclasses.
        schema_generator: Generates schema and schema names for the OpenAPI.

    """

    __slots__ = ()

    # API that needs to be set in subclasses:
    validation_error: ClassVar[type[Exception]]
    optimizer: ClassVar[type[BaseEndpointOptimizer]]
    schema_generator: ClassVar[type[BaseSchemaGenerator]]

    @classmethod
    @abc.abstractmethod
    def serialize(
        cls,
        structure: Any,
        *,
        renderer: Renderer,
    ) -> bytes:
        """Convert structured data to json bytestring."""
        raise NotImplementedError

    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """
        Customize how some objects are serialized into json.

        Only add types that are common for all potential plugins here.
        Should be called inside :meth:`serialize`.
        """
        if isinstance(to_serialize, (set, frozenset)):
            return list(to_serialize)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        raise DataRenderingError(
            f'Value {to_serialize} of type {type(to_serialize)} '
            'is not supported',
        )

    @classmethod
    @abc.abstractmethod
    def deserialize(
        cls,
        buffer: Raw,
        *,
        parser: Parser,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        """Convert json bytestring to structured data."""
        raise NotImplementedError

    @classmethod
    def deserialize_hook(
        cls,
        target_type: type[Any],
        to_deserialize: Any,
    ) -> Any:  # pragma: no cover
        """
        Customize how some objects are deserialized from json.

        Only add types that are common for all potential plugins here.
        Should be called inside :meth:`deserialize`.
        """
        raise RequestSerializationError(
            _CANNOT_DESERIALIZE_MSG.format(
                value=to_deserialize,
                type=type(to_deserialize),
                target_type=target_type,
            ),
        )

    @classmethod
    @abc.abstractmethod
    def from_python(
        cls,
        unstructured: Any,
        model: Any,
        *,
        strict: bool | None,
        extra_namespace: Mapping[str, Any] | None = None,
    ) -> Any:
        """
        Parse *unstructured* data from python primitives into *model*.

        Raises ``cls.validation_error`` when something cannot be parsed.

        Args:
            unstructured: Python objects to be parsed / validated.
            model: Python type to serve as a model.
                Can be any type hints that user can theoretically supply.
                Depends on the serialization plugin.
            strict: Whether we use more strict validation rules.
                For example, it is fine for a request validation
                to be less strict in some cases and allow type coercition.
                But, response types need to be strongly validated.
            extra_namespace: Optional namespace to load type annotations from.
                It is useful, when using stringified or lazy type annotations.

        Returns:
            Structured and validated data.

        .. versionchanged:: 0.13.0
            Added *extra_namespace* parameter.

        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def build_context_model(
        cls,
        name: str,
        fields: Mapping[str, ContextField],
    ) -> ContextModel:
        """
        Build the best model to parse the whole request context at once.

        All components of an endpoint are parsed in a single
        :meth:`from_python` call. This method builds the model for that call.
        Each serializer picks the fastest model type it can validate:
        it can be a :class:`typing.TypedDict`, a dataclass,
        a :class:`msgspec.Struct`, or anything else.

        Fields with defaults must not be required by the model.
        Default values must be used as-is, without any copies
        or default factories, because they are the real python defaults
        of the endpoint function. Use :func:`context_field_tuples`
        to get them in the form that most model constructors accept.

        Args:
            name: Name of the model to build. Not really important.
            fields: Mapping of field names to their annotations and defaults.

        Returns:
            Model and the way to convert its instances into keyword arguments.

        .. versionadded:: 0.16.0

        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def to_python(
        cls,
        structured: Any,
    ) -> Any:
        """
        Unstructure *structured* data from a model into Python primitives.

        Args:
            structured: Model instance.

        Returns:
            Unstructured data.

        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def serialize_validation_error(
        cls,
        exc: Exception,
    ) -> list[ErrorDetail]:
        """
        Convert specific serializer's validation errors into simple python data.

        Args:
            exc: A serialization exception to be serialized into simpler type.
                For example, pydantic has
                a complex :exc:`pydantic_core.ValidationError` type.
                That can't be converted to a simpler error message easily.

        Returns:
            Simple python object - exception converted to json.
        """
        raise NotImplementedError

    @classmethod
    def is_supported(cls, pluggable: Parser | Renderer) -> bool:
        """
        Is this parser or renderer supported?

        When defining custom serializers you can specify what kind
        of parser and renders you support.
        Adding a combination of unsupported serializer and parser / render
        will raise an import-time validation error.
        """
        return True  # By default all are supported
