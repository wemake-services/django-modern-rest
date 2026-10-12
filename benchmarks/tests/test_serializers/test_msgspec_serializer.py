from __future__ import annotations

import datetime as dt
import uuid
from typing import Final

import msgspec
from faker import Faker
from pytest_codspeed import BenchmarkFixture

from dmr.plugins.msgspec import (
    MsgspecJsonParser,
    MsgspecJsonRenderer,
    MsgspecSerializer,
)
from dmr.test import DMRRequestFactory

# All data is fixed, CodSpeed must measure the same thing on every run:
faker: Final = Faker()
faker.seed_instance(0)
_CREATED_AT: Final = dt.datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=dt.UTC)

#: A single call is measured in simulation mode,
#: repeat the work so that the cold first pass doesn't dominate:
_SERIALIZE_TIMES: Final = 10


class Role(msgspec.Struct):
    name: str
    uid: uuid.UUID


class Tag(msgspec.Struct):
    name: str
    premium: bool


class User(msgspec.Struct):
    email: str
    uid: uuid.UUID
    is_active: bool
    created_at: dt.datetime
    tags: list[Tag]
    role: Role


_TO_SERIALIZE: Final = [
    msgspec.convert(
        {
            'email': faker.email(),
            'uid': uuid.UUID(int=index),
            'is_active': True,
            'created_at': _CREATED_AT,
            'tags': [{'name': faker.name(), 'premium': False}],
            'role': {'name': faker.name(), 'uid': uuid.UUID(int=index + 1000)},
        },
        User,
    )
    for index in range(100)  # big, but realistic number
]


def test_msgspec_with_parser(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Test regular implementation with a parser."""

    parser = MsgspecJsonParser()
    body = msgspec.json.encode(_TO_SERIALIZE)
    request = dmr_rf.post(
        '/test',
        data=body,
        headers={'Content-Type': 'application/json'},
    )

    @benchmark
    def factory() -> None:
        MsgspecSerializer.deserialize(
            body,
            parser=parser,
            request=request,
            model=list[User],
        )


def test_msgspec_with_renderer(
    benchmark: BenchmarkFixture,
) -> None:
    """Test regular implementation with a renderer."""

    renderer = MsgspecJsonRenderer()

    @benchmark
    def factory() -> None:
        for _ in range(_SERIALIZE_TIMES):
            MsgspecSerializer.serialize(_TO_SERIALIZE, renderer=renderer)
