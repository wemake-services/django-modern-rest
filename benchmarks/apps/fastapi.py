import datetime as dt
import decimal
import enum
import uuid
from typing import Annotated

import fastapi
import pydantic

async_app = fastapi.FastAPI()
sync_app = fastapi.FastAPI()


class Level(enum.StrEnum):
    started = 'starter'
    mid = 'mid'
    pro = 'pro'


class Skill(pydantic.BaseModel):
    name: str
    description: str
    optional: bool
    level: Level


class Item(pydantic.BaseModel):
    name: str
    quality: int
    count: int
    rarety: int
    parts: list['Item']


class UserCreateModel(pydantic.BaseModel):
    email: str
    age: int
    height: float
    average_score: float
    balance: decimal.Decimal
    skills: list[Skill]
    aliases: dict[str, str | int]
    birthday: dt.datetime
    timezone_diff: dt.timedelta
    friends: list['UserModel']
    best_friend: 'UserModel | None'
    promocodes: list[uuid.UUID]
    items: list[Item]


class UserModel(UserCreateModel):
    uid: uuid.UUID


class QueryModel(pydantic.BaseModel):
    per_page: int
    count: int
    page: int
    filter: list[str]


class HeadersModel(pydantic.BaseModel):
    x_api_token: str
    x_request_origin: str


@async_app.post('/async/user/')
async def async_post(
    data: UserCreateModel,
    filters: Annotated[QueryModel, fastapi.Query()],
    headers: Annotated[HeadersModel, fastapi.Header()],
) -> UserModel:
    assert filters.filter[0] == 'fastapi', filters.filter
    return UserModel(
        uid=uuid.uuid4(),
        **data.model_dump(),
    )


@sync_app.post('/sync/user/')
def sync_post(
    data: UserCreateModel,
    filters: Annotated[QueryModel, fastapi.Query()],
    headers: Annotated[HeadersModel, fastapi.Header()],
) -> UserModel:
    assert filters.filter[0] == 'fastapi', filters.filter
    return UserModel(
        uid=uuid.uuid4(),
        **data.model_dump(),
    )
