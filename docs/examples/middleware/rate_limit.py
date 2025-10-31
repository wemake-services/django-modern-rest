from collections.abc import Callable
from http import HTTPStatus
from typing import ClassVar

from django.http import HttpRequest, HttpResponse

from django_modern_rest import Controller, ResponseDescription
from django_modern_rest.decorators import wrap_middleware
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.response import build_response


def rate_limit_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    """Middleware that simulates rate limiting."""

    def decorator(request: HttpRequest) -> HttpResponse:
        if request.headers.get('X-Rate-Limited') == 'true':
            return build_response(
                PydanticSerializer,
                raw_data={'detail': 'Rate limit exceeded'},
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
            )
        return get_response(request)

    return decorator


@wrap_middleware(
    rate_limit_middleware,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
    ),
)
def rate_limit_json(response: HttpResponse) -> HttpResponse:
    """Pass through the rate limit response."""
    return response


@rate_limit_json
class RateLimitedController(Controller[PydanticSerializer]):
    """Example controller with custom rate limit middleware."""

    responses: ClassVar[list[ResponseDescription]] = rate_limit_json.responses

    def post(self) -> dict[str, str]:
        return {'message': 'Request processed'}
