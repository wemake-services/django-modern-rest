import datetime as dt
import uuid
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from django_modern_rest import (
    Body,
    Controller,
    Headers,
    Query,
    ResponseDescription,
    validate,
    wrap_middleware,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


def custom_header_middleware(get_response):  # type: ignore[no-untyped-def]
    """Simple middleware that adds a custom header to response."""

    def middleware(request):  # type: ignore[no-untyped-def]  # noqa: WPS430
        response = get_response(request)
        response['X-Custom-Header'] = 'CustomValue'
        return response

    return middleware


def rate_limit_middleware(get_response):  # type: ignore[no-untyped-def]
    """Middleware that simulates rate limiting."""

    def middleware(request):  # type: ignore[no-untyped-def]  # noqa: WPS430
        if request.headers.get('X-Rate-Limited') == 'true':
            return JsonResponse(
                {'detail': 'Rate limit exceeded'},
                status=HTTPStatus.TOO_MANY_REQUESTS,
            )
        return get_response(request)

    return middleware


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
    # TODO: test and support `pydantic.Json` type


@final
class _UserOutput(_UserInput):
    uid: uuid.UUID
    token: str
    query: str
    start_from: dt.datetime | None


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
):
    async def patch(self, user_id: int) -> _UserInput:
        return _UserInput(
            email=self.parsed_body.email,
            age=user_id,
        )


@final
class UserReplaceController(Controller[PydanticSerializer]):
    @validate(
        ResponseDescription(
            return_type=_UserInput,
            status_code=HTTPStatus.OK,
        ),
    )
    async def put(self, user_id: int) -> HttpResponse:
        return JsonResponse({'email': 'new@email.com', 'age': user_id})


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
@wrap_middleware(
    ensure_csrf_cookie,
    converter=validate(
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.OK,
        )(
            lambda resp: resp,  # No conversion needed
        ),
    ),
)
class CsrfTokenController(Controller[PydanticSerializer]):
    """Controller to obtain CSRF token."""

    def get(self) -> dict[str, str]:
        """GET endpoint that ensures CSRF cookie is set."""
        return {'message': 'CSRF token set'}


@final
@wrap_middleware(
    csrf_protect,
    converter=validate(
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.FORBIDDEN,
        )(
            lambda resp: JsonResponse(
                {'detail': 'CSRF verification failed. Request aborted.'},
                status=HTTPStatus.FORBIDDEN,
            ),
        ),
    ),
)
class CsrfProtectedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    def post(self) -> _UserInput:
        return self.parsed_body


@final
@wrap_middleware(
    csrf_protect,
    converter=validate(
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.FORBIDDEN,
        )(
            lambda resp: JsonResponse(
                {'detail': 'CSRF verification failed. Request aborted.'},
                status=HTTPStatus.FORBIDDEN,
            ),
        ),
    ),
)
class AsyncCsrfProtectedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    async def post(self) -> _UserInput:
        return self.parsed_body


@final
@wrap_middleware(
    custom_header_middleware,
    converter=validate(
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.OK,
        )(
            lambda resp: resp,  # No conversion needed
        ),
    ),
)
class CustomHeaderController(Controller[PydanticSerializer]):
    """Controller with custom header middleware."""

    def get(self) -> dict[str, str]:
        """GET endpoint that returns simple data."""
        return {'message': 'Success'}


@final
@wrap_middleware(
    rate_limit_middleware,
    converter=validate(
        ResponseDescription(
            return_type=dict[str, str],
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
        )(
            lambda resp: resp,  # Already JSON from middleware
        ),
    ),
)
class RateLimitedController(
    Body[_UserInput],
    Controller[PydanticSerializer],
):
    """Controller with rate limiting middleware."""

    def post(self) -> _UserInput:
        """POST endpoint with rate limiting."""
        return self.parsed_body
