from collections.abc import Callable
from http import HTTPStatus
from typing import Any, TypeAlias

from django.http import HttpRequest, HttpResponse

from django_modern_rest import build_response
from django_modern_rest.plugins.pydantic import PydanticSerializer

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
                None,
                PydanticSerializer,
                raw_data={'detail': 'Rate limit exceeded'},
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
            )
        return get_response(request)

    return decorator
