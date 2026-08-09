from collections.abc import Callable
from contextlib import AbstractContextManager
from http import HTTPMethod, HTTPStatus
from typing import assert_type

from django.http import HttpRequest, HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test.types import (
    AssertAsyncThrottlingFixture,
    AssertThrottlingFixture,
    ReducedThrottlingFixture,
)
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle


class MyController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'ok'


def reduced_throttling_fixture(fixture: ReducedThrottlingFixture) -> None:
    manager = fixture(
        MyController,
        method='query',
        max_requests=1,
        rate=Rate.minute,
        when='before_auth',
    )
    assert_type(manager, AbstractContextManager[SyncThrottle | AsyncThrottle])
    with manager as throttle:
        assert_type(throttle, SyncThrottle | AsyncThrottle)

    fixture(
        MyController,
        method='GET',
        when='wrong',  # type: ignore[arg-type]
    )
    fixture(
        MyController,
        method=HTTPMethod.GET,
        unknown=1,  # type: ignore[call-arg]
    )
    fixture()  # type: ignore[call-arg]


def assert_throttling_fixture(
    fixture: AssertThrottlingFixture,
    request_factory: Callable[[], HttpRequest],
) -> None:
    assert_type(
        fixture(
            MyController,
            request_factory,
            max_requests=3,
            when='after_auth',
            success_status=HTTPStatus.OK,
        ),
        tuple[HttpResponse, SyncThrottle],
    )

    fixture(
        MyController,
        request_factory,
        when='wrong_when',  # type: ignore[arg-type]
    )


async def assert_async_throttling_fixture(
    fixture: AssertAsyncThrottlingFixture,
    request_factory: Callable[[], HttpRequest],
) -> None:
    assert_type(
        await fixture(
            MyController,
            request_factory,
            max_requests=3,
            rate=Rate.minute,
            when='after_auth',
            success_status=HTTPStatus.OK,
        ),
        tuple[HttpResponse, AsyncThrottle],
    )

    await fixture(
        MyController,
        request_factory,
        when='never',  # type: ignore[arg-type]
    )
