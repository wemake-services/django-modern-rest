from http import HTTPStatus
from typing import ClassVar, final


@final
class UnsolvableAnnotationsError(Exception):
    """
    Raised when we can't solve function's annotations using ``get_type_hints``.

    Only raised when there are no other options.
    """


@final
class EndpointMetadataError(Exception):
    """Raised when user didn't specify some required endpoint metadata."""


@final
class MethodNotAllowedError(Exception):
    """Raised when some API method is not allowed for the controller."""


class SerializationError(Exception):
    """
    Base class for all parsing and serialization errors.

    Do not use it directly, prefer exact exceptions for requests and responses.
    """

    #: All child classes must set this attribute:
    status_code: ClassVar[HTTPStatus] = HTTPStatus.UNPROCESSABLE_ENTITY


@final
class RequestSerializationError(SerializationError):
    """Raised when we fail to parse some request part."""

    status_code = HTTPStatus.BAD_REQUEST


@final
class ResponseSerializationError(SerializationError):
    """Raised when we fail to parse some response part."""
