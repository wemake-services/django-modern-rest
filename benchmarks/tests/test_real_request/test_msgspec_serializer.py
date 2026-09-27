from __future__ import annotations

import datetime as dt
import uuid
from typing import Final

import msgspec
from django.http import HttpResponseBase
from pytest_codspeed import BenchmarkFixture

from dmr import Body, Controller
from dmr.plugins.msgspec import (
    MsgspecSerializer,
)
from dmr.test import DMRRequestFactory


class Role(msgspec.Struct, frozen=True):
    name: str
    uid: uuid.UUID


class Tag(msgspec.Struct, frozen=True):
    name: str
    premium: bool


class User(msgspec.Struct, frozen=True):
    email: str
    uid: uuid.UUID
    is_active: bool
    created_at: dt.datetime
    tags: list[Tag]
    role: Role


_TO_SERIALIZE: Final = [
    User(
        email=f'user{index}@example.com',
        uid=uuid.UUID(int=index + 1),
        is_active=True,
        created_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        tags=[Tag(name=f'tag-{index}', premium=False)],
        role=Role(name='member', uid=uuid.UUID(int=index + 101)),
    )
    for index in range(100)
]
_BODY: Final = msgspec.json.encode(_TO_SERIALIZE)


class _MsgspecController(Controller[MsgspecSerializer]):
    def post(self, parsed_body: Body[list[User]]) -> int:
        return len(parsed_body)


def test_msgspec_parse_and_validate(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark through the request pipeline."""
    request = dmr_rf.post(
        '/test',
        data=_BODY,
        content_type='application/json',
    )
    controller = _MsgspecController()
    controller.setup(request)

    def factory() -> HttpResponseBase:
        return controller.dispatch(request)
