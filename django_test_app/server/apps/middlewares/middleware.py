import uuid
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, TypeAlias

from django.http import HttpRequest, HttpResponse

from dmr.errors import format_error
from dmr.plugins.pydantic import PydanticSerializer
from dmr.response import build_response

_CallableAny: TypeAlias = Callable[..., Any]


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
                raw_data=format_error('Rate limit exceeded'),
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
        request_id = uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]

        response = get_response(request)

        response['X-Request-ID'] = request_id

        return response

    return decorator
