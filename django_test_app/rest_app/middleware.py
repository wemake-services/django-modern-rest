from collections.abc import Callable
from http import HTTPStatus
from typing import Any, TypeAlias

from django.http import HttpRequest, HttpResponse, JsonResponse

_CallableAny: TypeAlias = Callable[..., Any]


def custom_header_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> _CallableAny:
    """Simple middleware that adds a custom header to response."""

    def middleware(request: HttpRequest) -> Any:  # noqa: WPS430
        response = get_response(request)
        response['X-Custom-Header'] = 'CustomValue'
        return response

    return middleware


def rate_limit_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> _CallableAny:
    """Middleware that simulates rate limiting."""

    def middleware(request: HttpRequest) -> Any:  # noqa: WPS430
        if request.headers.get('X-Rate-Limited') == 'true':
            return JsonResponse(
                {'detail': 'Rate limit exceeded'},
                status=HTTPStatus.TOO_MANY_REQUESTS,
            )
        return get_response(request)

    return middleware
