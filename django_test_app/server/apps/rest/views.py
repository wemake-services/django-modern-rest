import datetime as dt
import uuid
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, ClassVar, TypeAlias, final

import pydantic
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from django_modern_rest import (
    Body,
    Controller,
    Headers,
    Path,
    Query,
    ResponseDescription,
    validate,
    wrap_middleware,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.response import build_response
from server.apps.rest.middleware import (
    add_request_id_middleware,
    custom_header_middleware,
    rate_limit_middleware,
)

_CallableAny: TypeAlias = Callable[..., Any]


@wrap_middleware(
    csrf_protect,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.FORBIDDEN,
    ),
)
def csrf_protect_json(response: HttpResponse) -> HttpResponse:
    return build_response(
        PydanticSerializer,
        raw_data={'detail': 'CSRF verification failed. Request aborted.'},
        status_code=HTTPStatus.FORBIDDEN,
    )


@wrap_middleware(
    ensure_csrf_cookie,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def ensure_csrf_cookie_json(response: HttpResponse) -> HttpResponse:
    return response


@wrap_middleware(
    custom_header_middleware,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def custom_header_json(response: HttpResponse) -> HttpResponse:
    return response


@wrap_middleware(
    rate_limit_middleware,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
    ),
)
def rate_limit_json(response: HttpResponse) -> HttpResponse:
    return response


@wrap_middleware(
    add_request_id_middleware,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
)
def add_request_id_json(response: HttpResponse) -> HttpResponse:
    """Pass through response - request_id is added automatically."""
    return response


@wrap_middleware(
    login_required,
    ResponseDescription(
        return_type=dict[str, str],
        status_code=HTTPStatus.FOUND,
    ),
)
def login_required_json(response: HttpResponse) -> HttpResponse:
    """Convert Django's login_required redirect to JSON 401 response."""
    return build_response(
        PydanticSerializer,
        raw_data={'detail': 'Authentication credentials were not provided'},
        status_code=HTTPStatus.UNAUTHORIZED,
    )


@final
class _QueryData(pydantic.BaseModel):
    query: str = pydantic.Field(alias='q')
    start_from: dt.datetime | None = None


@final
class _CustomHeaders(pydantic.BaseModel):
    token: str = pydantic.Field(alias='X-API-Token')


class _UserInput(pydantic.BaseModel):
    email: str
    age: int


@final
class _UserOutput(_UserInput):
    uid: uuid.UUID
    token: str
    query: str
    start_from: dt.datetime | None


@final
class _UserPath(pydantic.BaseModel):
    user_id: int


@final
class UserCreateController(  # noqa: WPS215
    Query[_QueryData],
    Headers[_CustomHeaders],
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    def post(self) -> _UserOutput:
        return _UserOutput(
            uid=uuid.uuid4(),
            email=self.parsed_body.email,
            age=self.parsed_body.age,
            token=self.parsed_headers.token,
            query=self.parsed_query.query,
            start_from=self.parsed_query.start_from,
        )


@final
class UserListController(Controller[PydanticSerializer]):
    def get(self) -> list[_UserInput]:
        return [
            _UserInput(email='first@mail.ru', age=1),
            _UserInput(email='second@mail.ru', age=2),
        ]


@final
class UserUpdateController(
    Body[_UserInput],
    Controller[PydanticSerializer],
    Path[_UserPath],
):
    async def patch(self) -> _UserInput:
        return _UserInput(
            email=self.parsed_body.email,
            age=self.parsed_path.user_id,
        )


@final
class UserReplaceController(
    Controller[PydanticSerializer],
    Path[_UserPath],
):
    @validate(
        ResponseDescription(
            return_type=_UserInput,
            status_code=HTTPStatus.OK,
        ),
    )
    async def put(self) -> HttpResponse:
        return self.to_response({
            'email': 'new@email.com',
            'age': self.parsed_path.user_id,
        })


@final
class ParseHeadersController(
    Headers[_CustomHeaders],
    Controller[PydanticSerializer],
):
    def post(self) -> _CustomHeaders:
        return self.parsed_headers


@final
class AsyncParseHeadersController(
    Headers[_CustomHeaders],
    Controller[PydanticSerializer],
):
    async def post(self) -> _CustomHeaders:
        return self.parsed_headers


@final
@ensure_csrf_cookie_json
class CsrfTokenController(Controller[PydanticSerializer]):
    """Controller to obtain CSRF token."""

    responses: ClassVar[list[ResponseDescription]] = (
        ensure_csrf_cookie_json.responses
    )

    def get(self) -> dict[str, str]:
        """GET endpoint that ensures CSRF cookie is set."""
        message_key = 'message'  # noqa: WPS226
        return {message_key: 'CSRF token set'}


@final
@csrf_protect_json
class CsrfProtectedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    # Just add responses from middleware
    responses: ClassVar[list[ResponseDescription]] = csrf_protect_json.responses

    def post(self) -> _UserInput:
        return self.parsed_body


@final
@csrf_protect_json
class AsyncCsrfProtectedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    # Just add responses from middleware
    responses: ClassVar[list[ResponseDescription]] = csrf_protect_json.responses

    async def post(self) -> _UserInput:
        return self.parsed_body


@final
@custom_header_json
class CustomHeaderController(Controller[PydanticSerializer]):
    """Controller with custom header middleware."""

    responses: ClassVar[list[ResponseDescription]] = (
        custom_header_json.responses
    )

    def get(self) -> dict[str, str]:
        """GET endpoint that returns simple data."""
        return {'message': 'Success'}


@final
@rate_limit_json
class RateLimitedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    """Controller with rate limiting middleware."""

    responses: ClassVar[list[ResponseDescription]] = rate_limit_json.responses

    def post(self) -> _UserInput:
        """POST endpoint with rate limiting."""
        return self.parsed_body


@final
@add_request_id_json
class RequestIdController(Controller[PydanticSerializer]):
    """Controller that uses request_id added by middleware."""

    responses: ClassVar[list[ResponseDescription]] = (
        add_request_id_json.responses
    )

    def get(self) -> dict[str, str]:
        """GET endpoint that returns request_id from modified request."""
        # Access request.request_id that was added by middleware
        request_id = getattr(self.request, 'request_id', 'unknown')
        return {'request_id': request_id, 'message': 'Request ID tracked'}


@final
@login_required_json
class LoginRequiredController(Controller[PydanticSerializer]):
    """Controller that uses Django's login_required decorator.

    Demonstrates wrapping Django's built-in authentication decorators.
    Converts 302 redirect to JSON 401 response for REST API compatibility.
    """

    responses: ClassVar[list[ResponseDescription]] = (
        login_required_json.responses
    )

    def get(self) -> dict[str, str]:
        """GET endpoint that requires Django authentication."""
        # Access Django's authenticated user
        user = self.request.user
        username = user.username if user.is_authenticated else 'anonymous'

        return {
            'username': username,
            'message': 'Successfully accessed protected resource',
        }
