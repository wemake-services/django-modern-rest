from http import HTTPStatus
from typing import ClassVar

from django.http import HttpResponse
from project.app.middleware import (
    rate_limit_middleware,  # Don't forget to change
)

from django_modern_rest import Controller, ResponseDescription, wrap_middleware
from django_modern_rest.plugins.pydantic import PydanticSerializer


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
    responses: ClassVar[list[ResponseDescription]] = rate_limit_json.responses

    def post(self) -> dict[str, str]:
        return {'message': 'Request processed'}
