from http import HTTPStatus

from django.http import HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from django_modern_rest import Controller, ResponseSpec
from django_modern_rest.decorators import wrap_middleware
from django_modern_rest.plugins.pydantic import PydanticSerializer
from examples.middleware.csrf_protect_json import csrf_protect_json


# CSRF cookie for GET requests
@wrap_middleware(
    ensure_csrf_cookie,
    ResponseSpec(
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def ensure_csrf_cookie_json(response: HttpResponse) -> HttpResponse:
    """Return response ensuring CSRF cookie is set."""
    return response


@csrf_protect_json
class ProtectedController(Controller[PydanticSerializer]):
    """Protected API controller requiring CSRF token."""

    responses = csrf_protect_json.responses

    def get(self) -> dict[str, str]:
        """Get CSRF token."""
        return {'message': 'Use this endpoint to get CSRF token'}

    def post(self) -> dict[str, str]:
        """Protected endpoint requiring CSRF token."""
        return {'message': 'Successfully created resource'}


@ensure_csrf_cookie_json
class PublicController(Controller[PydanticSerializer]):
    responses = ensure_csrf_cookie_json.responses

    def get(self) -> dict[str, str]:
        """Public endpoint that sets CSRF cookie."""
        return {'message': 'CSRF cookie set'}


# run: {"controller": "PublicController", "method": "get", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
