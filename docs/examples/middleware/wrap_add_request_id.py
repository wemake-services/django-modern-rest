from http import HTTPStatus

from django.http import HttpResponse

from dmr import ResponseSpec
from dmr.decorators import wrap_middleware
from examples.middleware.add_request_id import add_request_id_middleware


@wrap_middleware(
    add_request_id_middleware,
    ResponseSpec(
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def add_request_id_json(response: HttpResponse) -> HttpResponse:
    """Pass through response - ``request_id`` is added automatically."""
    return response
