from __future__ import annotations

import datetime as dt
import uuid
from typing import Final

import pydantic
from pytest_codspeed import BenchmarkFixture

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.test import DMRRequestFactory


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
_BODY: Final = pydantic.TypeAdapter(list[User]).dump_json(_TO_SERIALIZE)


class _PydanticController(Controller[PydanticSerializer]):
    def post(self, parsed_body: Body[list[User]]) -> int:
        return len(parsed_body)


class _PydanticFastController(Controller[PydanticFastSerializer]):
    def post(self, parsed_body: Body[list[User]]) -> int:
        return len(parsed_body)


def test_pydantic_parse_and_validate(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark through the request pipeline."""
    request = dmr_rf.post(
        '/test',
        data=_BODY,
        content_type='application/json',
    )
    controller = _PydanticController()
    controller.setup(request)

    @benchmark
    def factory() -> None:
        for _ in range(10):
            controller.dispatch(request)


def test_pydantic_fast_parse_and_validate(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark through the request pipeline with the fast serializer."""
    request = dmr_rf.post(
        '/test',
        data=_BODY,
        content_type='application/json',
    )
    controller = _PydanticFastController()
    controller.setup(request)

    @benchmark
    def factory() -> None:
        for _ in range(100):
            controller.dispatch(request)
