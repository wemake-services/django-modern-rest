import datetime as dt
import decimal
import enum
import uuid

import fastapi
import pydantic
from apps import config

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


@async_app.post('/async/users/')
async def async_post(
    data: UserCreateModel,
) -> list[UserModel]:
    result = UserModel(
        uid=uuid.uuid4(),
        **data.model_dump(),
    )
    return [result] * config.RESPONSE_ITEMS


@sync_app.post('/sync/users/')
def sync_post(
    data: UserCreateModel,
) -> list[UserModel]:
    result = UserModel(
        uid=uuid.uuid4(),
        **data.model_dump(),
    )
    return [result] * config.RESPONSE_ITEMS
