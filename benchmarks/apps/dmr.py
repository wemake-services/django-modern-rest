import datetime as dt
import decimal
import enum
import uuid

import msgspec
from apps import config
from django.conf import settings
from django.core.handlers import asgi, wsgi
from django.urls import include

from dmr import Controller
from dmr.plugins.msgspec import BodyMsgspec, MsgspecSerializer
from dmr.routing import Router, path

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


class UserAsyncController(Controller[MsgspecSerializer]):
    async def post(
        self,
        parsed_body: BodyMsgspec[UserCreateModel],
    ) -> list[UserModel]:
        result = UserModel(
            uid=uuid.uuid4(),
            **msgspec.to_builtins(parsed_body),
        )
        return [result] * config.RESPONSE_ITEMS


class UserSyncController(Controller[MsgspecSerializer]):
    def post(
        self,
        parsed_body: BodyMsgspec[UserCreateModel],
    ) -> list[UserModel]:
        result = UserModel(
            uid=uuid.uuid4(),
            **msgspec.to_builtins(parsed_body),
        )
        return [result] * config.RESPONSE_ITEMS


router = Router(
    '',
    [
        path('async/users/', UserAsyncController.as_view(), name='async_users'),
        path('sync/users/', UserSyncController.as_view(), name='sync_users'),
    ],
)
urlpatterns = [
    path(
        router.prefix,
        include((router.urls, 'benchmark_app'), namespace='api'),
    ),
]
