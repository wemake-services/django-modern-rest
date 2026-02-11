from http import HTTPStatus
from typing import Final, final

import pydantic
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from django_modern_rest import Body, Controller, ResponseSpec
from django_modern_rest.decorators import wrap_middleware
from django_modern_rest.errors import format_error
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.response import build_response
from server.apps.middlewares.middleware import (
    add_request_id_middleware,
    custom_header_middleware,
    rate_limit_middleware,
)

_MESSAGE_KEY: Final = 'message'


@final
class _RequestWithID(HttpRequest):
    request_id: str


@wrap_middleware(
    csrf_protect,
    ResponseSpec(
        return_type=dict[str, list[dict[str, str]]],
        status_code=HTTPStatus.FORBIDDEN,
    ),
)
def csrf_protect_json(response: HttpResponse) -> HttpResponse:
    return build_response(
        PydanticSerializer,
        raw_data=format_error('CSRF verification failed. Request aborted.'),
        status_code=HTTPStatus.FORBIDDEN,
    )


@wrap_middleware(
    ensure_csrf_cookie,
    ResponseSpec(
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def ensure_csrf_cookie_json(response: HttpResponse) -> HttpResponse:
    return response


@wrap_middleware(
    custom_header_middleware,
    ResponseSpec(
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def custom_header_json(response: HttpResponse) -> HttpResponse:
    return response


@wrap_middleware(
    rate_limit_middleware,
    ResponseSpec(
        return_type=dict[str, str],
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
    ),
)
def rate_limit_json(response: HttpResponse) -> HttpResponse:
    return response


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


@wrap_middleware(
    login_required,
    ResponseSpec(
        return_type=dict[str, str],
        status_code=HTTPStatus.FOUND,
    ),
    ResponseSpec(  # Uses for proxy authed response with HTTPStatus.OK
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def login_required_json(response: HttpResponse) -> HttpResponse:
    """Convert Django's ``login_required`` redirect to JSON 401 response."""
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
class _UserInput(pydantic.BaseModel):
    email: str
    age: int = pydantic.Field(strict=True)


@final
@ensure_csrf_cookie_json
class CsrfTokenController(Controller[PydanticSerializer]):
    """Controller to obtain CSRF token."""

    responses = ensure_csrf_cookie_json.responses

    def get(self) -> dict[str, str]:
        """GET endpoint that ensures CSRF cookie is set."""
        return {_MESSAGE_KEY: 'CSRF token set'}


@final
@csrf_protect_json
class CsrfProtectedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    # Just add responses from middleware
    responses = csrf_protect_json.responses

    def post(self) -> _UserInput:
        return self.parsed_body


@final
@csrf_protect_json
class AsyncCsrfProtectedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    # Just add responses from middleware
    responses = csrf_protect_json.responses

    async def post(self) -> _UserInput:
        return self.parsed_body


@final
@custom_header_json
class CustomHeaderController(Controller[PydanticSerializer]):
    """Controller with custom header middleware."""

    responses = custom_header_json.responses

    def get(self) -> dict[str, str]:
        """GET endpoint that returns simple data."""
        return {_MESSAGE_KEY: 'Success'}


@final
@rate_limit_json
class RateLimitedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    """Controller with rate limiting middleware."""

    responses = rate_limit_json.responses

    def post(self) -> _UserInput:
        """POST endpoint with rate limiting."""
        return self.parsed_body


@final
@add_request_id_json
class RequestIdController(Controller[PydanticSerializer]):
    """Controller that uses ``request_id`` added by middleware."""

    responses = add_request_id_json.responses

    request: _RequestWithID

    def get(self) -> dict[str, str]:
        """GET endpoint that returns request_id from modified request."""
        return {
            'request_id': self.request.request_id,
            'message': 'Request ID tracked',
        }


@final
@login_required_json
class LoginRequiredController(Controller[PydanticSerializer]):
    """Controller that uses Django's ``login_required`` decorator.

    Demonstrates wrapping Django's built-in authentication decorators.
    Converts 302 redirect to JSON 401 response for REST API compatibility.
    """

    responses = login_required_json.responses

    def get(self) -> dict[str, str]:
        """GET endpoint that requires Django authentication."""
        # Access Django's authenticated user
        user = self.request.user
        username = user.username if user.is_authenticated else 'anonymous'

        return {
            'username': username,
            _MESSAGE_KEY: 'Successfully accessed protected resource',
        }
