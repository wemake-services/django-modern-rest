import abc
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    TypeAlias,
    TypeVar,
)

from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from dmr.errors import ErrorDetail
from dmr.exceptions import (
    InternalServerError,
    RequestSerializationError,
)
from dmr.parsers import Parser, Raw
from dmr.renderers import Renderer

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata

_CANNOT_DESERIALIZE_MSG: Final = _(
    'Value {value} of type {type} is not supported for {target_type}',
)

_ModelT = TypeVar('_ModelT')


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
        openapi:

    """

    __slots__ = ()

    # API that needs to be set in subclasses:
    validation_error: ClassVar[type[Exception]]
    optimizer: ClassVar[type['BaseEndpointOptimizer']]
    schema_generator: ClassVar[type['BaseSchemaGenerator']]

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
        raise InternalServerError(
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

        Returns:
            Structured and validated data.

        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def to_python(
        cls,
        structured: Any,
    ) -> Any:
        """
        Unarse *structured* data from a model into Python primitives.

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


class BaseEndpointOptimizer:
    """
    Plugins might often need to run some specific preparations for endpoints.

    To achieve that we provide an explicit API for that.
    """

    @classmethod
    @abc.abstractmethod
    def optimize_endpoint(cls, metadata: 'EndpointMetadata') -> None:
        """
        Optimize the endpoint.

        Args:
            metadata: Endpoint metadata to optimize.

        """
        raise NotImplementedError


SchemaDef: TypeAlias = tuple[
    dict[str, Any],
    dict[str, Any],
]


class BaseSchemaGenerator:
    """Generates JSON schema by the native serializer API."""

    @classmethod
    @abc.abstractmethod
    def get_schema(
        cls,
        model: Any,
        ref_template: str,
        *,
        used_for_response: bool = False,
    ) -> SchemaDef | None:
        """
        Provide JSON schema / OpenAPI spec for the given model.

        Args:
            model: Model to generate JSON schema for.
            ref_template: Reference template to use for the references.
            used_for_response: Is this schema used for the response or request.

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
