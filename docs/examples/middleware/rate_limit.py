from collections.abc import Callable
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse

from dmr import Controller, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.errors import ErrorModel, format_error
from dmr.plugins.pydantic import PydanticSerializer
from dmr.response import build_response


def rate_limit_middleware(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    """Middleware that simulates rate limiting."""

    def decorator(request: HttpRequest) -> HttpResponse:
        if request.headers.get('X-Rate-Limited') == 'true':
            return build_response(
                PydanticSerializer,
                raw_data=format_error('Rate limit exceeded'),
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
            )
        return get_response(request)

    return decorator


@wrap_middleware(
    rate_limit_middleware,
    ResponseSpec(
        return_type=ErrorModel,
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
    ),
)
def rate_limit_json(response: HttpResponse) -> HttpResponse:
    """Pass through the rate limit response."""
    return response


@rate_limit_json
class RateLimitedController(Controller[PydanticSerializer]):
    """Example controller with custom rate limit middleware."""

    responses = rate_limit_json.responses

    def post(self) -> dict[str, str]:
        return {'message': 'Request processed'}


# run: {"controller": "RateLimitedController", "method": "post", "url": "/api/ratelimit/"}  # noqa: ERA001, E501
# run: {"controller": "RateLimitedController", "method": "post", "headers": {"X-Rate-Limited": "true"}, "url": "/api/ratelimit/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
