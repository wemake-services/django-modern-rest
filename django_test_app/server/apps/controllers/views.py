import datetime as dt
import uuid
from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any, ClassVar, TypeAlias, final

import pydantic
from django.http import HttpResponse
from typing_extensions import override

from dmr import (  # noqa: WPS235
    Blueprint,
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
from dmr.errors import ErrorType
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
class UserCreateBlueprint(  # noqa: WPS215
    Query[_QueryData],
    Headers[_CustomHeaders],
    Body[_SimpleUserInput],
    Blueprint[PydanticSerializer],
):
    def post(self) -> _SimpleUserOutput:
        return _SimpleUserOutput(
            uid=uuid.uuid4(),
            email=self.parsed_body.email,
            age=self.parsed_body.age,
            token=self.parsed_headers.token,
            query=self.parsed_query.query,
            start_from=self.parsed_query.start_from,
        )


@final
class UserListBlueprint(Blueprint[PydanticSerializer]):
    def get(self) -> list[_SimpleUserInput]:
        return [
            _SimpleUserInput(email='first@example.org', age=1),
            _SimpleUserInput(email='second@example.org', age=2),
        ]


@final
class UserUpdateBlueprint(
    Body[_SimpleUserInput],
    Blueprint[PydanticSerializer],
    # It does not have `Path` on purpose to test `path()`'s native schema
):
    responses = (
        # Since we don't use `Path` component,
        # we need to add `NOT_FOUND` manually:
        ResponseSpec(Blueprint.error_model, status_code=HTTPStatus.NOT_FOUND),
    )

    async def patch(self) -> _SimpleUserInput:
        return _SimpleUserInput.model_validate(
            {
                'email': self.parsed_body.email,
                'age': self.kwargs['user_id'],
            },
            strict=False,
        )

    @override
    async def handle_async_error(
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
        return await super().handle_async_error(endpoint, controller, exc)


@final
class UserReplaceBlueprint(
    Blueprint[PydanticSerializer],
    Path[_UserPath],
):
    @validate(
        ResponseSpec(
            return_type=_SimpleUserInput,
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
    auth = (HttpBasicSync(),)

    def post(self) -> _CustomHeaders:
        return self.parsed_headers


@final
class AsyncParseHeadersController(
    Headers[_CustomHeaders],
    Controller[PydanticSerializer],
):
    @modify(auth=[HttpBasicAsync()])
    async def post(self) -> _CustomHeaders:
        return self.parsed_headers


@final
class ConstrainedUserController(
    Body[_ConstrainedUserSchema],
    Controller[PydanticSerializer],
):
    def post(self) -> _ConstrainedUserSchema:
        return self.parsed_body
