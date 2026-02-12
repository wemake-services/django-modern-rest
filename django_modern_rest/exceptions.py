from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar, final

if TYPE_CHECKING:
    from django_modern_rest.errors import ErrorDetail


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


@final
class InternalServerError(Exception):
    """
    Indicates that something is broken on our side.

    If ``settings.DEBUG`` is enabled, we share the details: what has happened.
    If it disabled, we hust show a generic message.
    """

    default_message: ClassVar[str] = 'Internal server error'
    status_code: ClassVar[HTTPStatus] = HTTPStatus.INTERNAL_SERVER_ERROR


@final
class ValidationError(Exception):
    """
    Raised when we cannot properly validate request or response models.

    It should be only raised when serializer raise
    its internal validation error.

    It is an universal way of handling validation errors
    from different serializers.
    """

    def __init__(
        self,
        payload: list['ErrorDetail'],
        *,
        status_code: HTTPStatus,
    ) -> None:
        """Set required status code attribute."""
        # No empty items are allowed:
        assert payload  # noqa: S101
        super().__init__(payload)
        self.payload = payload
        self.status_code = status_code


@final
class RequestSerializationError(Exception):
    """Raised when we fail to parse some request part."""

    status_code: ClassVar[HTTPStatus] = HTTPStatus.BAD_REQUEST


@final
class ResponseSchemaError(Exception):
    """
    Raised when we fail to validate some response part.

    Can only happen when response validation is enabled.
    Does not show up in the response schema if validation is disabled.
    """

    status_code: ClassVar[HTTPStatus] = HTTPStatus.UNPROCESSABLE_ENTITY


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


@final
class PermissionDeniedError(Exception):
    """Raised when user does not have permission to perform action."""

    status_code: ClassVar[HTTPStatus] = HTTPStatus.FORBIDDEN

    def __init__(self, msg: str = 'Permission denied') -> None:
        """Provides default error message."""
        super().__init__(msg)
