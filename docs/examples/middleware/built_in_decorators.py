from http import HTTPStatus
from typing import final

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from django_modern_rest import Controller, ResponseSpec
from django_modern_rest.decorators import wrap_middleware
from django_modern_rest.errors import ErrorModel, format_error
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.response import build_response


@wrap_middleware(
    login_required,
    ResponseSpec(
        return_type=ErrorModel,
        status_code=HTTPStatus.UNAUTHORIZED,
    ),
    ResponseSpec(  # Uses for proxy authed response with HTTPStatus.OK
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def login_required_json(response: HttpResponse) -> HttpResponse:
    """Convert Django's login_required redirect to JSON 401 response."""
    if response.status_code == HTTPStatus.FOUND:
        return build_response(
            PydanticSerializer,
            raw_data=format_error(
                'Authentication credentials were not provided',
            ),
            status_code=HTTPStatus.UNAUTHORIZED,
        )
    return response


@final
@login_required_json
class LoginRequiredController(Controller[PydanticSerializer]):
    """Controller that uses Django's login_required decorator.

    Demonstrates wrapping Django's built-in authentication decorators.
    Converts 302 redirect to JSON 401 response for REST API compatibility.
    """

    responses = login_required_json.responses

    def get(self) -> dict[str, str]:
        """GET endpoint that requires Django authentication."""
        # Access Django's authenticated user
        user = self.request.user
        username = user.username if user.is_authenticated else 'anonymous'  # type: ignore[attr-defined]

        return {
            'username': username,
            'message': 'Successfully accessed protected resource',
        }
