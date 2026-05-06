import json
from http import HTTPStatus
from typing import Final

import pytest
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.algorithms import LeakyBucket
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft

_ATTEMPTS: Final = 2
_RATE: Final = 10


class _SyncController(Controller[PydanticFastSerializer]):
    @modify(
        throttling=[
            SyncThrottle(
                _ATTEMPTS,
                _RATE,
                algorithm=LeakyBucket(),
            ),
        ],
    )
    def get(self) -> str:
        return 'inside'


def test_leaky_bucket_sync_fill_and_reject(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Fill the bucket to capacity, then get rejected."""
    # Two requests fill the bucket:
    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK

    # Third is rejected:
    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers == {
        'X-RateLimit-Limit': '2',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': str(_RATE // _ATTEMPTS),
        'Retry-After': str(_RATE // _ATTEMPTS),
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [
            {'msg': 'Too many requests', 'type': 'ratelimit'},
        ],
    })


def test_leaky_bucket_smooth_drain(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Verify smooth draining: partial time frees partial capacity."""
    # Fill the bucket:
    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert response.status_code == HTTPStatus.OK

    # Rejected while full:
    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    # After several seconds one token leaks:
    freezer.tick(delta=_RATE / _ATTEMPTS)

    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    # Bucket is full again - immediately rejected:
    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_leaky_bucket_full_drain(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """After full duration the bucket is empty again."""
    # Fill the bucket:
    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert response.status_code == HTTPStatus.OK

    # After full duration everything drains:
    freezer.tick(delta=_RATE)

    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    'rate',
    [Rate.second, Rate.minute, Rate.hour, Rate.day],
)
def test_leaky_bucket_rates(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    rate: Rate,
) -> None:
    """Rates work correctly with the leaky bucket."""

    class _Controller(Controller[PydanticFastSerializer]):
        throttling = [
            SyncThrottle(1, rate, algorithm=LeakyBucket()),
        ]

        def get(self) -> str:
            return 'ok'

    # First is ok:
    request = dmr_rf.get('/whatever/')
    response = _Controller.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    # Second is rate limited:
    request = dmr_rf.get('/whatever/')
    response = _Controller.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    # After full duration, it is ok:
    freezer.tick(delta=int(rate))

    request = dmr_rf.get('/whatever/')
    response = _Controller.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


class _TwoEndpointsController(Controller[PydanticFastSerializer]):
    @modify(
        throttling=[
            SyncThrottle(
                1,
                Rate.second,
                algorithm=LeakyBucket(),
            ),
        ],
    )
    def get(self) -> str:
        return 'get'

    @modify(
        throttling=[
            SyncThrottle(
                1,
                Rate.second,
                algorithm=LeakyBucket(),
            ),
        ],
    )
    def put(self) -> str:
        return 'put'


def test_leaky_bucket_per_endpoint_isolation(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Different endpoints have separate buckets."""
    # Fill GET bucket:
    request = dmr_rf.get('/whatever/')
    response = _TwoEndpointsController.as_view()(request)
    assert response.status_code == HTTPStatus.OK

    # GET is now rejected:
    request = dmr_rf.get('/whatever/')
    response = _TwoEndpointsController.as_view()(request)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    # PUT still works (separate bucket):
    request = dmr_rf.put('/whatever/')
    response = _TwoEndpointsController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    # Now it is also full:
    request = dmr_rf.put('/whatever/')
    response = _TwoEndpointsController.as_view()(request)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


_ODD_ATTEMPTS: Final = 3


class _AsyncController(Controller[PydanticFastSerializer]):
    throttling = [
        AsyncThrottle(
            _ODD_ATTEMPTS,
            _RATE,
            algorithm=LeakyBucket(),
            response_headers=[RateLimitIETFDraft()],
        ),
        AsyncThrottle(
            30,  # noqa: WPS432
            Rate.minute,
            algorithm=LeakyBucket(),
            response_headers=[RateLimitIETFDraft()],
            cache_key=RemoteAddr(name='min'),
        ),
    ]

    async def get(self) -> str:
        return 'ok'


@pytest.mark.asyncio
async def test_leaky_bucket_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Async controllers work with the leaky bucket algorithm."""
    # Fill the bucket:
    for _ in range(_ODD_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK

    # Rejected:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers == {
        'RateLimit-Policy': '3;w=10;name="RemoteAddr", 30;w=60;name="min"',
        'RateLimit': '"RemoteAddr";r=0;t=4',
        'Content-Type': 'application/json',
    }

    # After partial drain one more is allowed:
    freezer.tick(delta=4)  # `_ceil_div(10, 3)` result

    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    # After full drain two are allowed:
    freezer.tick(delta=_RATE)

    for _ in range(_ODD_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK

    # But, next are rejected:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers == {
        'RateLimit-Policy': '3;w=10;name="RemoteAddr", 30;w=60;name="min"',
        'RateLimit': '"RemoteAddr";r=0;t=4',
        'Content-Type': 'application/json',
    }
