import datetime as dt
import uuid
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, ClassVar, TypeAlias, final

import pydantic
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from django_modern_rest import (  # noqa: WPS235
    Blueprint,
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
class UserCreateBlueprint(  # noqa: WPS215
    Query[_QueryData],
    Headers[_CustomHeaders],
    Body[_UserInput],
    Blueprint[PydanticSerializer],
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
class UserListBlueprint(Blueprint[PydanticSerializer]):
    def get(self) -> list[_UserInput]:
        return [
            _UserInput(email='first@mail.ru', age=1),
            _UserInput(email='second@mail.ru', age=2),
        ]


@final
class UserUpdateBlueprint(
    Body[_UserInput],
    Blueprint[PydanticSerializer],
    Path[_UserPath],
):
    async def patch(self) -> _UserInput:
        return _UserInput(
            email=self.parsed_body.email,
            age=self.parsed_path.user_id,
        )


@final
class UserReplaceBlueprint(
    Blueprint[PydanticSerializer],
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
        return {'message': 'CSRF token set'}


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
