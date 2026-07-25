import contextlib
from http import HTTPMethod, HTTPStatus

import pytest
from dirty_equals import IsStr
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import (
    DMRAsyncRequestFactory,
    DMRRequestFactory,
    assert_async_throttling,
    assert_throttled,
    assert_throttling,
    reduced_throttling,
)
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft

_URL = '/whatever/'


class _SyncController(Controller[PydanticFastSerializer]):
    throttling = (
        SyncThrottle(5, Rate.minute),
        SyncThrottle(10, Rate.hour),
    )

    def get(self) -> str:
        return 'inside'

    @modify(throttling=None)
    def put(self) -> str:
        return 'inside'


class _AsyncController(Controller[PydanticFastSerializer]):
    throttling = (AsyncThrottle(3, Rate.hour),)

    async def get(self) -> str:
        return 'inside'


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


class _IETFController(Controller[PydanticFastSerializer]):
    # Emits `RateLimit`, not `X-RateLimit-Limit`:
    throttling = (
        SyncThrottle(5, Rate.minute, response_headers=[RateLimitIETFDraft()]),
    )

    def get(self) -> str:
        return 'inside'


def _throttled_response(
    controller_cls: type[Controller[PydanticFastSerializer]],
    dmr_rf: DMRRequestFactory,
) -> HttpResponse:
    view = controller_cls.as_view()
    with reduced_throttling(controller_cls) as throttle:
        for _ in range(throttle.max_requests):
            ok = view(dmr_rf.get(_URL))
            assert isinstance(ok, HttpResponse)
            assert ok.status_code == HTTPStatus.OK, ok.content
        throttled = view(dmr_rf.get(_URL))
    assert isinstance(throttled, HttpResponse)
    return throttled


def test_reduced_throttling_sync(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The endpoint is throttled after `max_requests` real requests."""
    view = _SyncController.as_view()
    with reduced_throttling(_SyncController) as throttle:
        assert throttle.max_requests == 2
        for _ in range(throttle.max_requests):
            ok = view(dmr_rf.get(_URL))
            assert isinstance(ok, HttpResponse)
            assert ok.status_code == HTTPStatus.OK, ok.content
        throttled = view(dmr_rf.get(_URL))

    assert isinstance(throttled, HttpResponse)
    assert_throttled(
        throttled,
        limit=2,
        reset=Rate.minute,
        retry_after=Rate.minute,
    )


def test_reduced_throttling_restores() -> None:
    """The endpoint's throttling is left untouched after the block."""
    endpoint = _SyncController.api_endpoints['GET']
    before = endpoint.metadata.throttling
    assert before is not None
    assert before[0].max_requests == 5

    with reduced_throttling(_SyncController):
        assert endpoint.metadata.throttling is not None
        assert endpoint.metadata.throttling[0].max_requests == 2

    assert endpoint.metadata.throttling is before
    assert endpoint.metadata.throttling[0].max_requests == 5


@pytest.mark.asyncio
async def test_reduced_throttling_async(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """`reduced_throttling` works for async controllers too."""
    view = _AsyncController.as_view()
    with reduced_throttling(_AsyncController) as throttle:
        for _ in range(throttle.max_requests):
            ok = await dmr_async_rf.wrap(view(dmr_async_rf.get(_URL)))
            assert isinstance(ok, HttpResponse)
            assert ok.status_code == HTTPStatus.OK, ok.content
        throttled = await dmr_async_rf.wrap(view(dmr_async_rf.get(_URL)))

    assert isinstance(throttled, HttpResponse)
    assert_throttled(throttled, limit=2)


def test_reduced_throttling_custom_max_requests(
    dmr_rf: DMRRequestFactory,
) -> None:
    """`max_requests` controls how many requests are needed."""
    view = _SyncController.as_view()
    with reduced_throttling(_SyncController, max_requests=1) as throttle:
        assert throttle.max_requests == 1
        ok = view(dmr_rf.get(_URL))
        assert isinstance(ok, HttpResponse)
        assert ok.status_code == HTTPStatus.OK, ok.content
        throttled = view(dmr_rf.get(_URL))

    assert isinstance(throttled, HttpResponse)
    assert_throttled(throttled, limit=1)


def test_reduced_throttling_no_throttling(dmr_rf: DMRRequestFactory) -> None:
    """Reducing an endpoint without throttling is a clear error."""
    stack = contextlib.ExitStack()
    with pytest.raises(ValueError, match='no throttling'):
        stack.enter_context(
            reduced_throttling(_SyncController, method=HTTPMethod.PUT),
        )

    # The `put` endpoint itself works fine (covers the handler):
    allowed = _SyncController.as_view()(dmr_rf.put(_URL))
    assert isinstance(allowed, HttpResponse)
    assert allowed.status_code == HTTPStatus.OK


def test_reduced_throttling_unknown_method() -> None:
    """Reducing a method the controller does not serve is a clear error."""
    stack = contextlib.ExitStack()
    with pytest.raises(ValueError, match='no endpoint'):
        stack.enter_context(
            reduced_throttling(_SyncController, method=HTTPMethod.DELETE),
        )


def test_reduced_throttling_before_auth(dmr_rf: DMRRequestFactory) -> None:
    """`line='before_auth'` targets the before-auth throttle line."""
    view = _SyncController.as_view()
    with reduced_throttling(_SyncController, line='before_auth') as throttle:
        for _ in range(throttle.max_requests):
            allowed = view(dmr_rf.get(_URL))
            assert allowed.status_code == HTTPStatus.OK
        rejected = view(dmr_rf.get(_URL))

    assert isinstance(rejected, HttpResponse)
    assert_throttled(rejected, limit=2)


def test_reduced_throttling_after_auth(dmr_rf: DMRRequestFactory) -> None:
    """`line='after_auth'` targets the after-auth throttle line."""
    view = _AfterAuthController.as_view()
    with reduced_throttling(
        _AfterAuthController,
        line='after_auth',
    ) as throttle:
        for _ in range(throttle.max_requests):
            allowed = view(dmr_rf.get(_URL))
            assert allowed.status_code == HTTPStatus.OK
        rejected = view(dmr_rf.get(_URL))

    assert isinstance(rejected, HttpResponse)
    assert_throttled(rejected, limit=2)


def test_reduced_throttling_line_empty() -> None:
    """Selecting a line with no throttles is a clear error."""
    stack = contextlib.ExitStack()
    with pytest.raises(ValueError, match='no throttling'):
        stack.enter_context(
            reduced_throttling(_SyncController, line='after_auth'),
        )


def test_assert_throttling_sync(dmr_rf: DMRRequestFactory) -> None:
    """The all-in-one driver reduces, drives requests, and asserts the 429."""
    response = assert_throttling(_SyncController, dmr_rf, _URL, limit=2)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_assert_async_throttling(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """The async all-in-one driver reduces, drives requests, asserts 429."""
    response = await assert_async_throttling(
        _AsyncController,
        dmr_async_rf,
        _URL,
        limit=2,
    )
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_throttle_replace() -> None:
    """`replace` copies a throttle with a new `max_requests`."""
    original = SyncThrottle(1000, Rate.minute)
    reduced = original.replace(max_requests=2)

    assert reduced.max_requests == 2
    assert original.max_requests == 1000  # original untouched
    assert reduced.duration_in_seconds == original.duration_in_seconds
    assert reduced.cache_key is original.cache_key


def test_assert_throttled_rejects_ok_response(
    dmr_rf: DMRRequestFactory,
) -> None:
    """`assert_throttled` fails on a non-throttled response."""
    response = _SyncController.as_view()(dmr_rf.get(_URL))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(AssertionError):
        assert_throttled(response)


def test_assert_throttled_missing_header(dmr_rf: DMRRequestFactory) -> None:
    """A missing expected header fails with a clear error, not `KeyError`."""
    response = _throttled_response(_IETFController, dmr_rf)
    with pytest.raises(AssertionError, match=r'X-RateLimit-Limit.*missing'):
        assert_throttled(response, limit=2)


def test_assert_throttled_detail_false(dmr_rf: DMRRequestFactory) -> None:
    """`detail=False` skips the error-body check; headers accept `str`."""
    response = _throttled_response(_SyncController, dmr_rf)
    assert_throttled(response, limit='2', detail=False)


def test_assert_throttled_matcher_header(dmr_rf: DMRRequestFactory) -> None:
    """Header expectations accept matcher objects for real-time tests."""
    response = _throttled_response(_SyncController, dmr_rf)
    assert_throttled(response, reset=IsStr())
