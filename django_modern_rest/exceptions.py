from http import HTTPStatus
from typing import ClassVar, final


@final
class UnsolvableAnnotationsError(Exception):
    """
    Raised when we can't solve function's annotations using ``get_type_hints``.

    Only raised when there are no other options.
    """


@final
class NegotiationDefinitionError(Exception):
    """
    Raised when we create correct negotiation protocol.

    Only raised during import time.
    """


@final
class EndpointMetadataError(Exception):
    """Raised when user didn't specify some required endpoint metadata."""


@final
class DataParsingError(Exception):
    """Raised when json/xml data cannot be parsed."""


class SerializationError(Exception):
    """
    Base class for all parsing and serialization errors.

    Do not use it directly, prefer exact exceptions for requests and responses.
    """

    #: Child classes can customize this attribute:
    status_code: ClassVar[HTTPStatus] = HTTPStatus.UNPROCESSABLE_ENTITY


@final
class RequestSerializationError(SerializationError):
    """Raised when we fail to parse some request part."""

    status_code = HTTPStatus.BAD_REQUEST


@final
class ResponseSerializationError(SerializationError):
    """Raised when we fail to parse some response part."""


@final
class NotAcceptableError(Exception):
    """Raised when client provides wrong ``Accept`` header."""

    status_code = HTTPStatus.NOT_ACCEPTABLE


@final
class NotAuthenticatedError(Exception):
    """Raised when we fail to authenticate a user."""

    status_code: ClassVar[HTTPStatus] = HTTPStatus.UNAUTHORIZED

    def __init__(self, msg: str = 'Not authenticated') -> None:
        """Provides default error message."""
        super().__init__(msg)
