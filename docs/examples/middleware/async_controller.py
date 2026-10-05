from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from dmr import Controller, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.errors import ErrorModel, format_error
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.response import build_response


def maintenance_middleware(
    get_response: Callable[[HttpRequest], Any],
) -> Callable[[HttpRequest], Any]:
    """Answers ``503`` while the site is in maintenance mode."""

    def decorator(request: HttpRequest) -> Any:
        if getattr(settings, 'MAINTENANCE_MODE', False):
            return build_response(
                PydanticFastSerializer,
                raw_data=format_error('Down for maintenance'),
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            )
        # For async controllers this is a coroutine, return it as is:
        return get_response(request)

    return decorator


@wrap_middleware(
    maintenance_middleware,
    ResponseSpec(
        return_type=ErrorModel,
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
    ),
)
def maintenance_json(response: HttpResponse) -> HttpResponse:
    """The middleware already returns JSON."""
    return response


@maintenance_json
class AsyncController(Controller[PydanticFastSerializer]):
    """Example async controller with the maintenance mode middleware."""

    responses = maintenance_json.responses

    async def get(self) -> dict[str, str]:
        # Your async logic here
        return {'message': 'async response'}


# run: {"controller": "AsyncController", "method": "get", "url": "/api/async/"}  # noqa: ERA001
