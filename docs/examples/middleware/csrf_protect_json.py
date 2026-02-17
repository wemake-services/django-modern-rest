from http import HTTPStatus

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect

from dmr import Controller, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.errors import ErrorModel, format_error
from dmr.plugins.pydantic import PydanticSerializer
from dmr.response import build_response


@wrap_middleware(
    csrf_protect,
    ResponseSpec(
        return_type=ErrorModel,
        status_code=HTTPStatus.FORBIDDEN,
    ),
)
def csrf_protect_json(response: HttpResponse) -> HttpResponse:
    """Convert CSRF failure responses to JSON."""
    return build_response(
        PydanticSerializer,
        raw_data=format_error(
            'CSRF verification failed. Request aborted.',
        ),
        status_code=HTTPStatus(response.status_code),
    )


@csrf_protect_json
class MyController(Controller[PydanticSerializer]):
    """Example controller using CSRF protection middleware."""

    responses = csrf_protect_json.responses

    def post(self) -> dict[str, str]:
        return {'message': 'ok'}
