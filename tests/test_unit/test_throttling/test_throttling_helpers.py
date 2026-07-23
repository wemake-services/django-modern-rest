from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from dirty_equals import IsStr
from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import (
    DMRAsyncRequestFactory,
    DMRRequestFactory,
    assert_throttled,
    throttle_state,
)
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.algorithms import (
    BaseThrottleAlgorithm,
    LeakyBucket,
    SimpleRate,
)
from dmr.throttling.backends import CachedRateLimit
from dmr.throttling.headers import RateLimitIETFDraft

if TYPE_CHECKING:
    from collections.abc import Callable

    from dmr.test import _ThrottleState  # noqa: WPS450


class _NoSaturateRate(SimpleRate):
    """SimpleRate that reports no saturated state, forcing the `incr` seed."""

    @override
    def saturated_state(  # type: ignore[override]
        self,
        throttle: SyncThrottle | AsyncThrottle,
    ) -> CachedRateLimit | None:
        # Exercises the base default (returns `None`) and forces the fallback:
        return BaseThrottleAlgorithm.saturated_state(self, throttle)


class _SyncController(Controller[PydanticFastSerializer]):
    throttling = [
        SyncThrottle(5, Rate.minute),
        SyncThrottle(10, Rate.hour),
    ]

    def get(self) -> str:
        return 'inside'

    @modify(throttling=None)
    def put(self) -> str:
        return 'inside'


class _AsyncController(Controller[PydanticFastSerializer]):
    throttling = [AsyncThrottle(3, Rate.hour)]

    async def get(self) -> str:
        return 'inside'


class _LeakyController(Controller[PydanticFastSerializer]):
    throttling = [SyncThrottle(3, Rate.minute, algorithm=LeakyBucket())]

    def get(self) -> str:
        return 'inside'


class _BigController(Controller[PydanticFastSerializer]):
    throttling = [SyncThrottle(1000, Rate.hour)]

    def get(self) -> str:
        return 'inside'


class _MultiController(Controller[PydanticFastSerializer]):
    # A coarse per-hour limit on the controller joined with a stricter
    # per-minute limit on the endpoint. Both must pass.
    throttling = (SyncThrottle(5, Rate.hour),)

    @modify(throttling=[SyncThrottle(1, Rate.minute)])
    def get(self) -> str:
        return 'inside'


class _NoSaturateSync(Controller[PydanticFastSerializer]):
    throttling = [SyncThrottle(2, Rate.minute, algorithm=_NoSaturateRate())]

    def get(self) -> str:
        return 'inside'


class _NoSaturateAsync(Controller[PydanticFastSerializer]):
    throttling = [AsyncThrottle(2, Rate.minute, algorithm=_NoSaturateRate())]

    async def get(self) -> str:
        return 'inside'


def _assert_ok(response: object) -> None:
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content


def _cover_handler_sync(
    controller: type[Controller[PydanticFastSerializer]],
    dmr_rf: DMRRequestFactory,
) -> None:
    # A request without `REMOTE_ADDR` has no cache key, so throttling is
    # skipped and the handler runs regardless of the seeded state.
    request = dmr_rf.get('/whatever/')
    request.META.pop('REMOTE_ADDR', None)
    _assert_ok(controller.as_view()(request))


async def _cover_handler_async(
    controller: type[Controller[PydanticFastSerializer]],
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    request = dmr_async_rf.get('/whatever/')
    request.META.pop('REMOTE_ADDR', None)
    _assert_ok(await dmr_async_rf.wrap(controller.as_view()(request)))


def test_exhaust_sync(dmr_rf: DMRRequestFactory) -> None:
    """`exhaust` saturates all throttles so the next request is throttled."""
    throttle_state(_SyncController).exhaust(dmr_rf.get('/whatever/'))

    response = _SyncController.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert_throttled(
        response,
        limit=5,
        reset=Rate.minute,
        retry_after=Rate.minute,
    )
    _cover_handler_sync(_SyncController, dmr_rf)


def test_exhaust_sync_via_fixture(
    dmr_rf: DMRRequestFactory,
    dmr_throttle_state: 'Callable[..., _ThrottleState]',
) -> None:
    """The `dmr_throttle_state` fixture exposes the same factory."""
    dmr_throttle_state(_SyncController).exhaust(dmr_rf.get('/whatever/'))

    response = _SyncController.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert_throttled(response)


def test_exhaust_no_throttling(dmr_rf: DMRRequestFactory) -> None:
    """Exhausting an endpoint without throttling is a clear error."""
    with pytest.raises(ValueError, match='no throttling'):
        throttle_state(_SyncController).exhaust(dmr_rf.put('/whatever/'))

    # The `put` endpoint itself works fine (covers the handler):
    _assert_ok(_SyncController.as_view()(dmr_rf.put('/whatever/')))


def test_exhaust_unknown_method(dmr_rf: DMRRequestFactory) -> None:
    """Exhausting a method the controller does not serve is a clear error."""
    with pytest.raises(ValueError, match='no endpoint'):
        throttle_state(_SyncController).exhaust(dmr_rf.delete('/whatever/'))


def test_exhaust_wrong_flavor(dmr_rf: DMRRequestFactory) -> None:
    """Using `exhaust` on async throttles raises a helpful error."""
    with pytest.raises(TypeError, match='aexhaust'):
        throttle_state(_AsyncController).exhaust(dmr_rf.get('/whatever/'))


@pytest.mark.asyncio
async def test_aexhaust_wrong_flavor(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Using `aexhaust` on sync throttles raises a helpful error."""
    with pytest.raises(TypeError, match='for sync controllers'):
        await throttle_state(_SyncController).aexhaust(
            dmr_async_rf.get('/whatever/'),
        )


@pytest.mark.asyncio
async def test_aexhaust_async(dmr_async_rf: DMRAsyncRequestFactory) -> None:
    """`aexhaust` saturates async throttles."""
    await throttle_state(_AsyncController).aexhaust(
        dmr_async_rf.get('/whatever/'),
    )

    response = await dmr_async_rf.wrap(
        _AsyncController.as_view()(dmr_async_rf.get('/whatever/')),
    )
    assert isinstance(response, HttpResponse)
    assert_throttled(response, limit=3)
    await _cover_handler_async(_AsyncController, dmr_async_rf)


def test_exhaust_leaky_bucket(dmr_rf: DMRRequestFactory) -> None:
    """`saturated_state` for `LeakyBucket` also seeds a full bucket."""
    throttle_state(_LeakyController).exhaust(dmr_rf.get('/whatever/'))

    response = _LeakyController.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert_throttled(response, limit=3)
    _cover_handler_sync(_LeakyController, dmr_rf)


def test_exhaust_large_rate_is_cheap(dmr_rf: DMRRequestFactory) -> None:
    """A big rate seeds in O(1): no 1000 requests to reach the limit."""
    throttle_state(_BigController).exhaust(dmr_rf.get('/whatever/'))

    response = _BigController.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert_throttled(response, limit=1000)
    _cover_handler_sync(_BigController, dmr_rf)


def test_exhaust_multiple_throttles(dmr_rf: DMRRequestFactory) -> None:
    """`exhaust` pre-fills every throttle on the endpoint in one call."""
    endpoint = _MultiController.api_endpoints['GET']
    assert len(endpoint.metadata.throttling or ()) == 2

    throttle_state(_MultiController).exhaust(dmr_rf.get('/whatever/'))

    # Both the per-minute and the per-hour rule are at their limit now:
    controller = _MultiController()
    controller.setup(dmr_rf.get('/whatever/'))
    for throttle in endpoint.metadata.throttling or ():
        assert isinstance(throttle, SyncThrottle)
        usage = throttle.report_usage(endpoint, controller)
        assert usage['X-RateLimit-Remaining'] == '0', usage

    # The endpoint is rejected, reporting the stricter per-minute rule first:
    response = _MultiController.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert_throttled(
        response,
        limit=1,
        reset=Rate.minute,
        retry_after=Rate.minute,
    )
    _cover_handler_sync(_MultiController, dmr_rf)


def test_exhaust_fallback_incr_loop(dmr_rf: DMRRequestFactory) -> None:
    """When the algorithm has no saturated state, seeding replays `incr`."""
    throttle_state(_NoSaturateSync).exhaust(dmr_rf.get('/whatever/'))

    response = _NoSaturateSync.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert_throttled(response, limit=2)
    _cover_handler_sync(_NoSaturateSync, dmr_rf)


@pytest.mark.asyncio
async def test_aexhaust_fallback_incr_loop(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Async seeding also falls back to replaying `incr`."""
    await throttle_state(_NoSaturateAsync).aexhaust(
        dmr_async_rf.get('/whatever/'),
    )

    response = await dmr_async_rf.wrap(
        _NoSaturateAsync.as_view()(dmr_async_rf.get('/whatever/')),
    )
    assert isinstance(response, HttpResponse)
    assert_throttled(response, limit=2)
    await _cover_handler_async(_NoSaturateAsync, dmr_async_rf)


def test_exhaust_skips_without_cache_key(dmr_rf: DMRRequestFactory) -> None:
    """A throttle whose cache key is `None` is silently skipped."""
    request = dmr_rf.get('/whatever/')
    request.META.pop('REMOTE_ADDR', None)  # `RemoteAddr` now returns `None`
    throttle_state(_SyncController).exhaust(request)

    other = dmr_rf.get('/whatever/')
    other.META.pop('REMOTE_ADDR', None)
    _assert_ok(_SyncController.as_view()(other))  # nothing was seeded


@pytest.mark.asyncio
async def test_aexhaust_skips_without_cache_key(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Async: a throttle whose cache key is `None` is silently skipped."""
    request = dmr_async_rf.get('/whatever/')
    request.META.pop('REMOTE_ADDR', None)
    await throttle_state(_AsyncController).aexhaust(request)  # does not raise


def test_assert_throttled_detail_false(dmr_rf: DMRRequestFactory) -> None:
    """`detail=False` skips the error-body check; headers accept `str`."""
    throttle_state(_SyncController).exhaust(dmr_rf.get('/whatever/'))
    response = _SyncController.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert_throttled(response, limit='5', detail=False)


def test_assert_throttled_matcher_header(dmr_rf: DMRRequestFactory) -> None:
    """Header expectations accept matcher objects for real-time tests."""
    throttle_state(_SyncController).exhaust(dmr_rf.get('/whatever/'))
    response = _SyncController.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert_throttled(response, reset=IsStr())


def test_assert_throttled_missing_header(dmr_rf: DMRRequestFactory) -> None:
    """A missing expected header fails with a clear error, not `KeyError`."""

    class _Ctrl(Controller[PydanticFastSerializer]):
        # This provider emits `RateLimit`, not `X-RateLimit-Limit`:
        throttling = (
            SyncThrottle(
                1,
                Rate.minute,
                response_headers=[RateLimitIETFDraft()],
            ),
        )

        def get(self) -> str:
            return 'inside'

    throttle_state(_Ctrl).exhaust(dmr_rf.get('/whatever/'))
    response = _Ctrl.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    with pytest.raises(AssertionError, match=r'X-RateLimit-Limit.*missing'):
        assert_throttled(response, limit=1)
    _cover_handler_sync(_Ctrl, dmr_rf)


def test_assert_throttled_rejects_ok_response(
    dmr_rf: DMRRequestFactory,
) -> None:
    """`assert_throttled` fails on a non-throttled response."""
    response = _SyncController.as_view()(dmr_rf.get('/whatever/'))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(AssertionError):
        assert_throttled(response)
