from http import HTTPStatus
from typing import TYPE_CHECKING, final

from django.conf import settings
from django.http import HttpRequest
from django.http.request import HttpHeaders
from django.middleware.csrf import CsrfViewMiddleware

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer


def ensure_csrf(controller: 'Controller[BaseSerializer]') -> None:
    """
    Raise ``APIError`` (403) if the CSRF check fails.

    Does not perform the second CSRF check if it was processed before.
    Since it uses the standard Django tooling, the default middleware
    checks ``csrf_processing_done`` which is set on each successful check.
    """
    from dmr.response import APIError  # noqa: PLC0415

    reason = _check_csrf_failure(controller.request)

    if reason is not None:
        raise APIError(
            controller.format_error(reason),
            status_code=HTTPStatus.FORBIDDEN,
        )


def csrf_header_name() -> str:
    """
    Convert ``CSRF_HEADER_NAME`` from the ``META`` form to the HTTP form.

    Django stores this setting as a ``request.META`` key,
    like ``HTTP_X_CSRFTOKEN``, while OpenAPI needs the header name
    that a client sends, like ``X-Csrftoken``. HTTP header names
    are case-insensitive, so the exact casing does not matter.
    """
    header_name = HttpHeaders.parse_header_name(settings.CSRF_HEADER_NAME)
    return settings.CSRF_HEADER_NAME if header_name is None else header_name


@final
class _EnsureCsrfToken(CsrfViewMiddleware):
    """
    CSRF check middleware that returns the rejection reason.

    Used for checking CSRF tokens manually.
    """

    def _reject(self, request: HttpRequest, reason: str) -> str:
        from dmr.security.csrf import csrf_message  # noqa: PLC0415

        # Return the failure reason instead of an ``HttpResponse``.
        # Expose detailed csrf failure reason on DEBUG mode.
        # Otherwise, provide default placeholder reason.
        return csrf_message(reason)


def _check_csrf_failure(request: HttpRequest) -> str | None:
    """Perform CSRF validation using ``_EnsureCsrfToken``."""
    check = _EnsureCsrfToken(lambda _: None)  # type: ignore[arg-type]
    check.process_request(request)
    return check.process_view(request, None, (), {})  # type: ignore[arg-type, return-value]
