import abc
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from django.http import HttpHeaders

from django_modern_rest.exceptions import (
    RequestSerializationError,
    ResponseSerializationError,
)

if TYPE_CHECKING:
    from django_modern_rest.endpoint import EndpointMetadata
    from django_modern_rest.internal.json import FromJson

_ModelT = TypeVar('_ModelT')


class BaseSerializer:
    """Abstract base class for JSON serialization."""

    __slots__ = ()

    # API that needs to be set in subclasses:
    validation_error: ClassVar[type[Exception]]
    optimizer: ClassVar[type['BaseEndpointOptimizer']]

    # API that have defaults:
    content_type: ClassVar[str] = 'application/json'

    @classmethod
    @abc.abstractmethod
    def to_json(cls, structure: Any) -> bytes:
        """Convert structured data to json bytestring."""
        raise NotImplementedError

    @classmethod
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """
        Customize how some objects are serialized into json.

        Only add types that are common for all potential plugins here.
        Should be called inside :meth:`to_json`.
        """
        if isinstance(to_serialize, HttpHeaders):
            return dict(to_serialize)
        raise ResponseSerializationError(
            f'Value {to_serialize} of type {type(to_serialize)} '
            'is not supported',
        )

    @classmethod
    @abc.abstractmethod
    def from_json(cls, buffer: 'FromJson') -> Any:
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
        Should be called inside :meth:`from_json`.
        """
        raise RequestSerializationError(
            f'Value {to_deserialize} of type {type(to_deserialize)} '
            f'is not supported for {target_type}',
        )

    @classmethod
    @abc.abstractmethod
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
                Can be any type hints that user can theoretically supply.
                Depends on the serialization plugin.
            strict: Whether we use more strict validation rules.
                For example, it is fine for a request validation
                to be less strict in some cases and allow type coercition.
                But, response types need to be strongly validated.

        Raises:
            validation_error: When parsing can't be done.

        Returns:
            Structured and validated data.
        """
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def error_to_json(cls, error: Exception) -> Any:
        """Serialize an exception to json the best way possible."""


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
