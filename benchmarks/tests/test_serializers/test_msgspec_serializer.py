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

faker: Final = Faker()


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
            'uid': uuid.uuid4(),
            'is_active': True,
            'created_at': dt.datetime.now(dt.UTC),
            'tags': [{'name': faker.name(), 'premium': False}],
            'role': {'name': faker.name(), 'uid': uuid.uuid4()},
        },
        User,
    )
    for _ in range(100)  # big, but realistic number
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
        MsgspecSerializer.serialize(_TO_SERIALIZE, renderer=renderer)
