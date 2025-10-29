from http import HTTPStatus
from typing import ClassVar

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect

from django_modern_rest import (
    Controller,
    ResponseDescription,
    build_response,
    wrap_middleware,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


@wrap_middleware(
    csrf_protect,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.FORBIDDEN,
    ),
)
def csrf_protect_json(response: HttpResponse) -> HttpResponse:
    """Convert CSRF failure responses to JSON."""
    return build_response(
        PydanticSerializer,
        raw_data={
            'detail': 'CSRF verification failed. Request aborted.',
        },
        status_code=HTTPStatus(response.status_code),
    )


@csrf_protect_json
class MyController(Controller[PydanticSerializer]):
    """Example controller using CSRF protection middleware."""

    responses: ClassVar[list[ResponseDescription]] = csrf_protect_json.responses

    def post(self) -> dict[str, str]:
        return {'message': 'ok'}
