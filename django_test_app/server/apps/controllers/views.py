import datetime as dt
import uuid
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, ClassVar, TypeAlias, final

import pydantic
from django.http import HttpResponse

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


class _UserInput(pydantic.BaseModel):
    email: str
    age: int = pydantic.Field(strict=True)


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
            _UserInput(email='first@example.org', age=1),
            _UserInput(email='second@example.org', age=2),
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
        ResponseSpec(
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
