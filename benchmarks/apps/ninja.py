import datetime as dt
import decimal
import enum
import uuid

from django.conf import settings
from django.core.handlers import asgi, wsgi
from django.http import HttpRequest
from django.urls import path
from django.utils.crypto import get_random_string

if not settings.configured:
    settings.configure(
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS='*',
        DEBUG=False,
        SECRET_KEY=get_random_string(50),
    )

from apps import config
from ninja import NinjaAPI, Schema

async_app = asgi.ASGIHandler()
sync_app = wsgi.WSGIHandler()


class Level(enum.StrEnum):
    started = 'starter'
    mid = 'mid'
    pro = 'pro'


class Skill(Schema):
    name: str
    description: str
    optional: bool
    level: Level


class Item(Schema):
    name: str
    quality: int
    count: int
    rarety: int
    parts: list['Item']


class UserCreateModel(Schema):
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


api = NinjaAPI()


@api.post('/async/users/')
async def async_post(
    request: HttpRequest,
    data: UserCreateModel,
) -> list[UserModel]:
    result = UserModel(
        uid=uuid.uuid4(),
        **data.model_dump(),
    )
    return [result] * config.RESPONSE_ITEMS


@api.post('/sync/users/')
def sync_post(
    request: HttpRequest,
    data: UserCreateModel,
) -> list[UserModel]:
    result = UserModel(
        uid=uuid.uuid4(),
        **data.model_dump(),
    )
    return [result] * config.RESPONSE_ITEMS


urlpatterns = [
    path('', api.urls),
]
