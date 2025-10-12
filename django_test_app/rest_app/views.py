import datetime as dt
import uuid
from typing import final

import pydantic
from django.http import HttpResponse, JsonResponse

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import (
    Body,
    Headers,
    PydanticSerializer,
    Query,
    rest,
)


@final
class _QueryData(pydantic.BaseModel):
    query: str = pydantic.Field(alias='q')
    start_from: dt.datetime | None = None

    # TODO: provide base model types with preset configs?
    model_config = pydantic.ConfigDict(extra='forbid')


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
    @rest(return_dto=_UserInput)
    async def put(self, user_id: int) -> HttpResponse:
        return JsonResponse({'email': 'new@email.com', 'age': user_id})
