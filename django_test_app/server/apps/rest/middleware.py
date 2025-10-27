import uuid
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, TypeAlias

from django.http import HttpRequest, HttpResponse

from django_modern_rest import build_response
from django_modern_rest.plugins.pydantic import PydanticSerializer

_CallableAny: TypeAlias = Callable[..., Any]
_USER_TOKEN_PREFIX: str = 'user_'  # noqa: S105


def _extract_user_id(token: str) -> int | None:
    """Extract user ID from token, return None if invalid."""
    try:
        return int(token.replace(_USER_TOKEN_PREFIX, ''))
    except ValueError:
        return None


def custom_header_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> _CallableAny:
    """Simple middleware that adds a custom header to response."""

    def decorator(request: HttpRequest) -> Any:
        response = get_response(request)
        response['X-Custom-Header'] = 'CustomValue'
        return response

    return decorator


def rate_limit_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> _CallableAny:
    """Middleware that simulates rate limiting."""

    def decorator(request: HttpRequest) -> Any:
        if request.headers.get('X-Rate-Limited') == 'true':
            return build_response(
                PydanticSerializer,
                raw_data={'detail': 'Rate limit exceeded'},
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
            )
        return get_response(request)

    return decorator


def add_request_id_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> _CallableAny:
    """Middleware that adds request_id to both request and response.

    This demonstrates the two-phase middleware pattern:
    1. Process request BEFORE calling get_response (adds request.request_id)
    2. Process response AFTER calling get_response (adds X-Request-ID header)
    """

    def decorator(request: HttpRequest) -> Any:
        request_id = str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]

        response = get_response(request)

        response['X-Request-ID'] = request_id

        return response

    return decorator


def auth_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> _CallableAny:
    """Middleware that simulates authentication.

    Adds user_id and authenticated flag to request based on X-Auth-Token header.
    This mimics Django's AuthenticationMiddleware behavior.
    """

    def decorator(request: HttpRequest) -> Any:  # noqa: WPS231
        token = request.headers.get('X-Auth-Token')
        if token and token.startswith(_USER_TOKEN_PREFIX):
            user_id = _extract_user_id(token)
            if user_id is None:
                request.authenticated = False  # type: ignore[attr-defined]
            else:
                request.user_id = user_id  # type: ignore[attr-defined]
                request.authenticated = True  # type: ignore[attr-defined]
        else:
            request.authenticated = False  # type: ignore[attr-defined]

        response = get_response(request)

        if hasattr(request, 'authenticated') and request.authenticated:
            response['X-Authenticated'] = 'true'

        return response

    return decorator


def require_auth_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> _CallableAny:
    """Strict auth middleware that returns 401 for unauth requests."""

    def decorator(request: HttpRequest) -> Any:
        token = request.headers.get('X-Auth-Token')

        if not token or not token.startswith(_USER_TOKEN_PREFIX):
            return build_response(
                PydanticSerializer,
                raw_data={'detail': 'Authentication required'},
                status_code=HTTPStatus.UNAUTHORIZED,
            )

        user_id = _extract_user_id(token)
        if user_id is None:
            return build_response(
                PydanticSerializer,
                raw_data={'detail': 'Invalid authentication token'},
                status_code=HTTPStatus.UNAUTHORIZED,
            )

        request.user_id = user_id  # type: ignore[attr-defined]
        request.authenticated = True  # type: ignore[attr-defined]

        response = get_response(request)
        response['X-Authenticated'] = 'true'

        return response

    return decorator
