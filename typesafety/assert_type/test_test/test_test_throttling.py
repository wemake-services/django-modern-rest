from collections.abc import Callable
from http import HTTPMethod, HTTPStatus
from typing import assert_type

from django.http import HttpRequest, HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import (
    assert_async_throttling,
    assert_throttling,
    reduced_throttling,
)
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle


class MyController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'ok'


def test_reduced_throttling() -> None:
    manager = reduced_throttling(
        MyController,
        method='query',
        max_requests=1,
        rate=Rate.minute,
        when='before_auth',
    )
    with manager as throttle:
        assert_type(throttle, SyncThrottle | AsyncThrottle)

    reduced_throttling(
        MyController,
        method='GET',
        when='wrong',  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    )
    reduced_throttling(
        MyController,
        method=HTTPMethod.GET,
        unknown=1,  # type: ignore[call-arg]  # ty: ignore[unknown-argument]
    )
    reduced_throttling()  # type: ignore[call-arg]  # ty: ignore[missing-argument]


def test_assert_throttling(
    request_factory: Callable[[], HttpRequest],
) -> None:
    assert_type(
        assert_throttling(
            MyController,
            request_factory,
            max_requests=3,
            when='after_auth',
            success_status=HTTPStatus.OK,
        ),
        tuple[HttpResponse, SyncThrottle],
    )

    assert_throttling(
        MyController,
        request_factory,
        when='wrong_when',  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    )


async def test_assert_async_throttling(
    request_factory: Callable[[], HttpRequest],
) -> None:
    assert_type(
        await assert_async_throttling(
            MyController,
            request_factory,
            max_requests=3,
            rate=Rate.minute,
            when='after_auth',
            success_status=HTTPStatus.OK,
        ),
        tuple[HttpResponse, AsyncThrottle],
    )

    await assert_async_throttling(
        MyController,
        request_factory,
        when='never',  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    )
