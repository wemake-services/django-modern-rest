import datetime as dt
import decimal
import enum
import uuid
from typing import Annotated

import msgspec
from django.conf import settings
from django.core.handlers import asgi, wsgi
from django.urls import include, path

from django_modern_rest import Body, Controller, Headers, Query, Router
from django_modern_rest.plugins.msgspec import MsgspecSerializer

if not settings.configured:
    settings.configure(
        ROOT_URLCONF=__name__,
        DMR_SETTINGS={'validate_responses': False},
        ALLOWED_HOSTS='*',
        DEBUG=False,
    )

async_app = asgi.ASGIHandler()
sync_app = wsgi.WSGIHandler()


class Level(enum.StrEnum):
    started = 'starter'
    mid = 'mid'
    pro = 'pro'


class Skill(msgspec.Struct):
    name: str
    description: str
    optional: bool
    level: Level


class Item(msgspec.Struct):
    name: str
    quality: int
    count: int
    rarety: int
    parts: list['Item']


class UserCreateModel(msgspec.Struct):
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


class HeadersModel(msgspec.Struct):
    token: str = msgspec.field(name='X-API-Token')
    origin: str = msgspec.field(name='X-Request-Origin')


class QueryModel(msgspec.Struct):
    per_page: Annotated[list[int], msgspec.Meta(min_length=1, max_length=1)]
    count: Annotated[list[int], msgspec.Meta(min_length=1, max_length=1)]
    page: Annotated[list[int], msgspec.Meta(min_length=1, max_length=1)]
    filter: list[str]


class UserAsyncController(
    Controller[MsgspecSerializer],
    Body[UserCreateModel],
    Headers[HeadersModel],
    Query[QueryModel],
):
    async def post(self) -> UserModel:
        assert self.parsed_query.filter[0] == 'dmr', self.parsed_query
        return UserModel(
            uid=uuid.uuid4(),
            **msgspec.to_builtins(self.parsed_body),
        )


class UserSyncController(
    Controller[MsgspecSerializer],
    Body[UserCreateModel],
    Headers[HeadersModel],
    Query[QueryModel],
):
    def post(self) -> UserModel:
        assert self.parsed_query.filter[0] == 'dmr', self.parsed_query
        return UserModel(
            uid=uuid.uuid4(),
            **msgspec.to_builtins(self.parsed_body),
        )


router = Router([
    path('async/user/', UserAsyncController.as_view(), name='async_users'),
    path('sync/user/', UserSyncController.as_view(), name='sync_users'),
])
urlpatterns = [
    path('', include((router.urls, 'benchmark_app'), namespace='api')),
]
