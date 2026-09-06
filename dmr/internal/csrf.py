from http import HTTPStatus
from typing import TYPE_CHECKING, Final, final

from django.conf import settings
from django.http import HttpRequest
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

_CSRF_FAILED_MSG: Final = _('CSRF Failed: {reason}')
_NON_DEBUG_CSRF_FAILED_REASON: Final = 'Forbidden.'


@final
class _EnsureCsrfToken(CsrfViewMiddleware):
    """
    CSRF check middleware that returns the rejection reason.

    Used for checking CSRF tokens manually.
    """

    def _reject(self, request: HttpRequest, reason: str) -> str:
        # Return the failure reason instead of an ``HttpResponse``.
        # Expose detailed csrf failure reason on DEBUG mode.
        # Otherwise, provide default placeholder reason.

        if settings.DEBUG:
            return reason

        return _NON_DEBUG_CSRF_FAILED_REASON


def _check_csrf_failure(request: HttpRequest) -> tuple[bool, str | None]:
    """Perform CSRF validation using ``_EnsureCsrfToken``."""
    check = _EnsureCsrfToken(lambda _: None)  # type: ignore[arg-type]
    check.process_request(request)
    reason = check.process_view(request, None, (), {})  # type: ignore[arg-type]
    is_failed = reason is not None

    return is_failed, reason  # type: ignore[return-value]


def ensure_csrf(controller: 'Controller[BaseSerializer]') -> None:
    """Raise ``APIError`` (403) if the CSRF check fails."""
    from dmr.response import APIError  # noqa: PLC0415

    is_failed, reason = _check_csrf_failure(controller.request)

    if is_failed:
        raise APIError(
            controller.format_error(_CSRF_FAILED_MSG.format(reason=reason)),
            status_code=HTTPStatus.FORBIDDEN,
        )
