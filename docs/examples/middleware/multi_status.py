from collections.abc import Callable
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse

from django_modern_rest import (
    ResponseDescription,
    build_response,
    wrap_middleware,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


def custom_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    """Dummy middleware for demonstration purposes."""

    def decorator(request: HttpRequest) -> HttpResponse:
        """Just pass the request through unchanged."""
        return get_response(request)

    return decorator


@wrap_middleware(
    custom_middleware,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.BAD_REQUEST,
    ),
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.UNAUTHORIZED,
    ),
)
def multi_status_middleware(response: HttpResponse) -> HttpResponse:
    """Handle multiple status codes."""
    if response.status_code == HTTPStatus.BAD_REQUEST:
        return build_response(
            PydanticSerializer,
            raw_data={'error': 'Bad request'},
            status_code=HTTPStatus(response.status_code),
        )
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        return build_response(
            PydanticSerializer,
            raw_data={'error': 'Unauthorized'},
            status_code=HTTPStatus(response.status_code),
        )
    return response
