from __future__ import annotations

import datetime as dt
import uuid
from typing import Final

import pydantic
from faker import Faker
from pytest_codspeed import BenchmarkFixture

from dmr.plugins.msgspec import MsgspecJsonParser, MsgspecJsonRenderer
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.test import DMRRequestFactory

faker: Final = Faker()


class Role(pydantic.BaseModel):
    name: str
    uid: uuid.UUID


class Tag(pydantic.BaseModel):
    name: str
    premium: bool


class User(pydantic.BaseModel):
    email: str
    uid: uuid.UUID
    is_active: bool
    created_at: dt.datetime
    tags: list[Tag]
    role: Role


_TO_SERIALIZE: Final = [
    User.model_validate({
        'email': faker.email(),
        'uid': uuid.uuid4(),
        'is_active': True,
        'created_at': dt.datetime.now(dt.UTC),
        'tags': [{'name': faker.name(), 'premium': False}],
        'role': {'name': faker.name(), 'uid': uuid.uuid4()},
    })
    for _ in range(100)  # big, but realistic number
]


def test_pyndatic_with_parser(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Test regular implementation with a parser."""

    parser = MsgspecJsonParser()
    body = pydantic.TypeAdapter(list[User]).dump_json(_TO_SERIALIZE)
    request = dmr_rf.post(
        '/test',
        data=body,
        headers={'Content-Type': 'application/json'},
    )

    @benchmark
    def factory() -> None:
        PydanticSerializer.deserialize(
            body,
            parser=parser,
            request=request,
            model=list[User],
        )


def test_pyndatic_with_renderer(
    benchmark: BenchmarkFixture,
) -> None:
    """Test regular implementation with a renderer."""

    renderer = MsgspecJsonRenderer()

    @benchmark
    def factory() -> None:
        PydanticSerializer.serialize(_TO_SERIALIZE, renderer=renderer)


def test_pyndatic_fast_deserialize(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Test optimized version with a single deserialize call."""

    parser = MsgspecJsonParser()
    body = pydantic.TypeAdapter(list[User]).dump_json(_TO_SERIALIZE)
    request = dmr_rf.post(
        '/test',
        data=body,
        headers={'Content-Type': 'application/json'},
    )

    @benchmark
    def factory() -> None:
        PydanticFastSerializer.deserialize(
            body,
            parser=parser,
            request=request,
            model=list[User],
        )


def test_pydantic_fast_serialize(
    benchmark: BenchmarkFixture,
) -> None:
    """Test optimized version with a single serialize call."""

    renderer = MsgspecJsonRenderer()

    @benchmark
    def factory() -> None:
        PydanticFastSerializer.serialize(_TO_SERIALIZE, renderer=renderer)
