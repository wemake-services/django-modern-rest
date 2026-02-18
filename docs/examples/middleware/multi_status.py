from collections.abc import Callable
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse

from dmr import ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.plugins.pydantic import PydanticSerializer
from dmr.response import build_response


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
    ResponseSpec(
        return_type=dict[str, str],
        status_code=HTTPStatus.BAD_REQUEST,
    ),
    ResponseSpec(
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
