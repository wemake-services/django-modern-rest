import datetime as dt
import uuid
from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any, ClassVar, TypeAlias, final

import pydantic
from django.http import HttpResponse

from dmr import (
    Body,
    Controller,
    Headers,
    Path,
    Query,
    ResponseSpec,
    modify,
    validate,
)
from dmr.endpoint import Endpoint
from dmr.errors import ErrorType, wrap_handler
from dmr.plugins.pydantic import PydanticSerializer
from server.apps.controllers.auth import HttpBasicAsync, HttpBasicSync

_CallableAny: TypeAlias = Callable[..., Any]


@final
class _QueryData(pydantic.BaseModel):
    __dmr_cast_null__: ClassVar[frozenset[str]] = frozenset(('start_from',))

    query: str = pydantic.Field(alias='q')
    start_from: dt.datetime | None = None


@final
class _CustomHeaders(pydantic.BaseModel):
    token: str = pydantic.Field(alias='X-API-Token')


class _SimpleUserInput(pydantic.BaseModel):
    email: str
    age: int = pydantic.Field(gt=0, strict=True)


@final
class _SimpleUserOutput(_SimpleUserInput):
    uid: uuid.UUID
    token: str
    query: str
    start_from: dt.datetime | None


@final
class _UserPath(pydantic.BaseModel):
    user_id: Annotated[int, pydantic.Field(ge=1)]


@final
class _ConstrainedUserSchema(pydantic.BaseModel):
    username: str = pydantic.Field(
        min_length=3,
        max_length=20,  # noqa: WPS432
        pattern=r'^[a-z0-9_]+$',
    )
    age: int = pydantic.Field(ge=18, le=100, strict=True)  # noqa: WPS432
    score: float = pydantic.Field(gt=0, le=10, strict=True)  # noqa: WPS432


@final
class UsersController(Controller[PydanticSerializer]):
    def post(
        self,
        parsed_query: Query[_QueryData],
        parsed_headers: Headers[_CustomHeaders],
        parsed_body: Body[_SimpleUserInput],
    ) -> _SimpleUserOutput:
        return _SimpleUserOutput(
            uid=uuid.uuid4(),
            email=parsed_body.email,
            age=parsed_body.age,
            token=parsed_headers.token,
            query=parsed_query.query,
            start_from=parsed_query.start_from,
        )

    def get(self) -> list[_SimpleUserInput]:
        return [
            _SimpleUserInput(email='first@example.org', age=1),
            _SimpleUserInput(email='second@example.org', age=2),
        ]


@final
class UserUpdateController(Controller[PydanticSerializer]):
    async def handle_validate_error(
        self,
        endpoint: Endpoint,
        controller: Controller[PydanticSerializer],
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, pydantic.ValidationError):
            return self.to_error(
                self.format_error(
                    'Object does not exist',
                    loc=['parsed_path', 'user_id'],
                    error_type=ErrorType.not_found,
                ),
                status_code=HTTPStatus.NOT_FOUND,
            )
        raise exc from None

    @modify(
        error_handler=wrap_handler(handle_validate_error),
        extra_responses=[
            # Since we don't use `Path` component,
            # we need to add `NOT_FOUND` manually:
            ResponseSpec(
                Controller.error_model,
                status_code=HTTPStatus.NOT_FOUND,
            ),
        ],
    )
    async def patch(
        self,
        # It does not have `Path` on purpose to test `path()`'s native schema
        parsed_body: Body[_SimpleUserInput],
    ) -> _SimpleUserInput:
        return _SimpleUserInput.model_validate(
            {
                'email': parsed_body.email,
                'age': self.kwargs['user_id'],
            },
            strict=False,
        )

    @validate(
        ResponseSpec(
            return_type=_SimpleUserInput,
            status_code=HTTPStatus.OK,
        ),
    )
    async def put(self, parsed_path: Path[_UserPath]) -> HttpResponse:
        return self.to_response({
            'email': 'new@email.com',
            'age': parsed_path.user_id,
        })


@final
class ParseHeadersController(Controller[PydanticSerializer]):
    auth = (HttpBasicSync(),)

    def post(self, parsed_headers: Headers[_CustomHeaders]) -> _CustomHeaders:
        return parsed_headers


@final
class AsyncParseHeadersController(Controller[PydanticSerializer]):
    @modify(auth=[HttpBasicAsync()])
    async def post(
        self,
        parsed_headers: Headers[_CustomHeaders],
    ) -> _CustomHeaders:
        return parsed_headers


@final
class ConstrainedUserController(Controller[PydanticSerializer]):
    def post(
        self,
        parsed_body: Body[_ConstrainedUserSchema],
    ) -> _ConstrainedUserSchema:
        return parsed_body
