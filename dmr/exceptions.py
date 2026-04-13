from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar, Final, final

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from dmr.errors import ErrorDetail

_NOT_AUTHENTICATED_MSG: Final = _('Not authenticated')
_TOO_MANY_REQUESTS: Final = _('Too many requests')


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
class DataParsingError(Exception):
    """Raised when input data cannot be parsed."""


@final
class DataRenderingError(Exception):
    """Raised when output data cannot be properly renderer."""

    status_code: ClassVar[HTTPStatus] = HTTPStatus.INTERNAL_SERVER_ERROR


@final
class InternalServerError(Exception):
    """
    Indicates that something is broken on our side.

    If ``settings.DEBUG`` is enabled, we share the details: what has happened.
    If it disabled, we hust show a generic message.
    """

    default_message: ClassVar[str | Promise] = _('Internal server error')
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
        status_code: HTTPStatus = HTTPStatus.UNPROCESSABLE_ENTITY,
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

    default_message: ClassVar[str | Promise] = _NOT_AUTHENTICATED_MSG
    status_code: ClassVar[HTTPStatus] = HTTPStatus.UNAUTHORIZED

    def __init__(self, msg: str | Promise | None = None) -> None:
        """Provides default error message."""
        # Circular import:
        from dmr.errors import ErrorType  # noqa: PLC0415

        super().__init__(msg or self.default_message)
        self.error_type = ErrorType.security


@final
class TooManyRequestsError(Exception):
    """Raised when user fails the throttling check."""

    default_message: ClassVar[str | Promise] = _TOO_MANY_REQUESTS
    status_code: ClassVar[HTTPStatus] = HTTPStatus.TOO_MANY_REQUESTS

    def __init__(
        self,
        msg: str | Promise | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Provides default error message."""
        # Circular import:
        from dmr.errors import ErrorType  # noqa: PLC0415

        super().__init__(msg or self.default_message)
        self.headers = headers
        self.error_type = ErrorType.ratelimit
