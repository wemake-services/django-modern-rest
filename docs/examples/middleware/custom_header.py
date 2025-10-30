from collections.abc import Callable
from typing import Any, TypeAlias

from django.http import HttpRequest, HttpResponse

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
