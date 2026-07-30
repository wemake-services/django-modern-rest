from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from django.http import HttpRequest
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

_CSRF_FAILED_MSG: Final = _('CSRF Failed: {reason}')


class _EnsureCsrfToken(CsrfViewMiddleware):
    """
    CSRF check middleware that returns the rejection reason.

    Used for checking CSRF tokens manually.
    """

    def _reject(self, request: HttpRequest, reason: str) -> str:
        # Return the failure reason instead of an ``HttpResponse``.
        return reason


def _get_csrf_failure_reason(request: HttpRequest) -> str | None:
    """Perform CSRF validation using ``_EnsureCsrfToken``."""
    check = _EnsureCsrfToken(lambda _: None)  # type: ignore[arg-type]
    check.process_request(request)
    return check.process_view(request, None, (), {})  # type: ignore[arg-type, return-value]


def ensure_csrf(controller: 'Controller[BaseSerializer]') -> None:
    """Raise ``APIError`` (403) if the CSRF check fails."""
    from dmr.response import APIError  # noqa: PLC0415

    reason = _get_csrf_failure_reason(controller.request)
    if reason:
        raise APIError(
            controller.format_error(_CSRF_FAILED_MSG.format(reason=reason)),
            status_code=HTTPStatus.FORBIDDEN,
        )
