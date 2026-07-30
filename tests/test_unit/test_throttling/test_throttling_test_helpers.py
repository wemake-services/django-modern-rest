import json
from http import HTTPMethod, HTTPStatus
from typing import Any, Final

import pydantic
import pytest
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot
from polyfactory.factories.pydantic_factory import ModelFactory

from dmr import Body, Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import (
    DMRAsyncRequestFactory,
    DMRRequestFactory,
    reduced_throttling,
)
from dmr.test.types import (
    AssertAsyncThrottlingFixture,
    AssertThrottlingFixture,
    ThrottlingWhen,
)
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import (
    RateLimitIETFDraft,
    RetryAfter,
    XRateLimit,
)

_URL: Final = '/whatever/'


class _SyncController(Controller[PydanticFastSerializer]):
    throttling = (
        SyncThrottle(5, Rate.minute),
        SyncThrottle(10, Rate.hour),
    )

    def get(self) -> str:
        return 'inside'

    @modify(throttling=None)
    def put(self) -> str:
        raise NotImplementedError


@pytest.mark.parametrize('rate', [Rate.minute, Rate.hour, Rate.day])
def test_reduced_throttling_sync_rate(
    dmr_assert_throttling: AssertThrottlingFixture,
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    rate: Rate,
) -> None:
    """The endpoint is throttled after `max_requests` real requests."""
    max_requests = 3

    response, throttle = dmr_assert_throttling(
        _SyncController,
        lambda: dmr_rf.get(_URL),
        rate=rate,
        max_requests=max_requests,
    )
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert throttle.duration_in_seconds == rate
    assert throttle.max_requests == max_requests

    with pytest.raises(ValueError, match='no throttling'):
        # But, `PUT` is not throttled:
        dmr_assert_throttling(
            _SyncController,
            lambda: dmr_rf.put(_URL),
            rate=rate,
        )


def test_reduced_throttling_restores() -> None:
    """The endpoint's throttling is left untouched after the block."""
    endpoint = _SyncController.api_endpoints['GET']
    before = endpoint.metadata.throttling_before_auth
    assert before is not None
    assert before[0].max_requests == 5
    assert before == endpoint.metadata.throttling

    with reduced_throttling(_SyncController, method=HTTPMethod.GET):
        assert endpoint.metadata.throttling_before_auth is not None
        assert endpoint.metadata.throttling_before_auth[0].max_requests == 2

    assert endpoint.metadata.throttling_before_auth is before
    assert endpoint.metadata.throttling_before_auth[0].max_requests == 5

    # But, it raises when no throttling is given:
    with pytest.raises(ValueError, match='no throttling'):
        reduced_throttling(  # noqa: PLC2801
            _SyncController,
            method=HTTPMethod.PUT,
        ).__enter__()


class _ExampleModel(pydantic.BaseModel):
    email: str
    unique_id: int


class _ExampleModelFactory(ModelFactory[_ExampleModel]):
    __use_examples__ = True


class _AsyncController(Controller[PydanticFastSerializer]):
    throttling = (AsyncThrottle(3, Rate.hour),)

    async def post(self, parsed_body: Body[_ExampleModel]) -> _ExampleModel:
        return parsed_body


@pytest.mark.asyncio
@pytest.mark.parametrize('rate', [Rate.minute, Rate.hour, Rate.day])
async def test_reduced_throttling_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    dmr_assert_async_throttling: AssertAsyncThrottlingFixture,
    *,
    rate: Rate,
) -> None:
    """`reduced_throttling` works for async controllers too."""
    max_requests = 3

    response, throttle = await dmr_assert_async_throttling(
        _AsyncController,
        lambda: dmr_async_rf.post(
            _URL,
            data=_ExampleModelFactory.build().model_dump(mode='json'),
        ),
        rate=rate,
        max_requests=max_requests,
    )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })
    assert throttle.duration_in_seconds == rate
    assert throttle.max_requests == max_requests

    # But, sync controllers can't be used with async assert:
    with pytest.raises(AssertionError, match='SyncThrottle'):
        await dmr_assert_async_throttling(
            _SyncController,
            lambda: dmr_async_rf.get(
                _URL,
                data=_ExampleModelFactory.build().model_dump(mode='json'),
            ),
            rate=rate,
        )


class _AfterAuthController(Controller[PydanticFastSerializer]):
    # `runs_before_auth=False` puts this throttle in the after-auth line,
    # while its `REMOTE_ADDR` key still resolves for anonymous requests.
    throttling = (
        SyncThrottle(
            5,
            Rate.minute,
            cache_key=RemoteAddr(runs_before_auth=False),
        ),
    )

    def get(self) -> str:
        return 'inside'


@pytest.mark.parametrize(
    ('controller_cls', 'when'),
    [
        (_SyncController, 'before_auth'),
        (_SyncController, 'any'),
        (_AfterAuthController, 'after_auth'),
        (_AfterAuthController, 'any'),
    ],
)
def test_reduced_throttling_when(
    dmr_assert_throttling: AssertThrottlingFixture,
    dmr_rf: DMRRequestFactory,
    *,
    controller_cls: type[Controller[Any]],
    when: ThrottlingWhen,
) -> None:
    """`when='before_auth'` targets the before-auth throttle line."""
    response, throttle = dmr_assert_throttling(
        controller_cls,
        lambda: dmr_rf.get(_URL),
        when=when,
    )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    if when == 'before_auth':
        assert throttle.cache_key.runs_before_auth is True
    elif when == 'after_auth':
        assert throttle.cache_key.runs_before_auth is False


def test_reduced_throttling_when_incorrect(
    dmr_assert_throttling: AssertThrottlingFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """`when='before_auth'` targets the before-auth throttle line."""
    with pytest.raises(AssertionError, match='wrong'):
        dmr_assert_throttling(
            _SyncController,
            lambda: dmr_rf.get(_URL),
            when='wrong',  # type: ignore[arg-type]
        )


def test_throttling_missing_endpoint(
    dmr_assert_throttling: AssertThrottlingFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Missing endpoints raise."""
    with pytest.raises(ValueError, match='no endpoint'):
        dmr_assert_throttling(
            _SyncController,
            lambda: dmr_rf.post(_URL),
        )


def test_reduced_throttling_when_empty() -> None:
    """Selecting a when with no throttles is a clear error."""
    with pytest.raises(ValueError, match='no throttling'):
        reduced_throttling(  # noqa: PLC2801
            _SyncController,
            method=HTTPMethod.GET,
            when='after_auth',
        ).__enter__()
    with pytest.raises(ValueError, match='no throttling'):
        reduced_throttling(  # noqa: PLC2801
            _AfterAuthController,
            method=HTTPMethod.GET,
            when='before_auth',
        ).__enter__()


@pytest.mark.parametrize(
    'headers',
    [
        RetryAfter(),
        XRateLimit(),
        RateLimitIETFDraft(),
    ],
)
def test_assert_throttling_header_provider(
    dmr_rf: DMRRequestFactory,
    dmr_assert_throttling: AssertThrottlingFixture,
    *,
    headers: RetryAfter | XRateLimit | RateLimitIETFDraft,
) -> None:
    """The driver checks the headers of a non-default provider too."""

    class _Controller(Controller[PydanticFastSerializer]):
        throttling = (SyncThrottle(5, Rate.minute, response_headers=[headers]),)

        def get(self) -> str:
            return 'inside'

    response, _ = dmr_assert_throttling(
        _Controller,
        lambda: dmr_rf.get(_URL),
    )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
