from contextlib import AbstractContextManager
from http import HTTPMethod
from typing import assert_type

from django.http import HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, SyncThrottle
from dmr_pytest import (
    AssertAsyncThrottlingFixture,
    AssertThrottledFixture,
    AssertThrottlingFixture,
    ReducedThrottlingFixture,
)


class MyController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'ok'


def reduced_throttling_fixture(fixture: ReducedThrottlingFixture) -> None:
    manager = fixture(
        MyController,
        method=HTTPMethod.POST,
        max_requests=1,
        line='before_auth',
    )
    assert_type(manager, AbstractContextManager[SyncThrottle | AsyncThrottle])
    with manager as throttle:
        assert_type(throttle, SyncThrottle | AsyncThrottle)

    fixture(MyController, line='wrong')  # type: ignore[arg-type]
    fixture(MyController, unknown=1)  # type: ignore[call-arg]
    fixture()  # type: ignore[call-arg]


def assert_throttled_fixture(
    fixture: AssertThrottledFixture,
    response: HttpResponse,
) -> None:
    assert_type(
        fixture(
            response,
            headers={'X-RateLimit-Remaining': 0},
            detail=False,
        ),
        None,
    )

    fixture(response, detail='yes')  # type: ignore[arg-type]
    fixture(response, unknown=1)  # type: ignore[call-arg]


def assert_throttling_fixture(
    fixture: AssertThrottlingFixture,
    request_factory: DMRRequestFactory,
) -> None:
    assert_type(
        fixture(
            MyController,
            request_factory,
            '/url/',
            method=HTTPMethod.PUT,
            max_requests=3,
            line='after_auth',
            headers={'RateLimit': 'whatever'},
            detail=False,
        ),
        HttpResponse,
    )

    # Sync helpers require a sync request factory:
    fixture(MyController, DMRAsyncRequestFactory(), '/url/')  # type: ignore[arg-type]
    fixture(MyController, request_factory)  # type: ignore[call-arg]


async def assert_async_throttling_fixture(
    fixture: AssertAsyncThrottlingFixture,
    request_factory: DMRAsyncRequestFactory,
) -> None:
    assert_type(
        await fixture(
            MyController,
            request_factory,
            '/url/',
            method=HTTPMethod.PUT,
            max_requests=3,
            line='after_auth',
            headers={'RateLimit': 'whatever'},
            detail=False,
        ),
        HttpResponse,
    )

    # Async helpers require an async request factory:
    await fixture(MyController, DMRRequestFactory(), '/url/')  # type: ignore[arg-type]
