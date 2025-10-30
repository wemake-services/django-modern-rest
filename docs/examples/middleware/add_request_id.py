import uuid
from collections.abc import Callable
from typing import Any, TypeAlias

from django.http import HttpRequest, HttpResponse

_CallableAny: TypeAlias = Callable[..., Any]


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
