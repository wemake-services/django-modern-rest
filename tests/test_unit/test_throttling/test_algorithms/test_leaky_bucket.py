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
from dmr.throttling.backends.django_cache import UnsafeCacheBackendWarning
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft

_ATTEMPTS: Final = 2
_RATE: Final = 10

with pytest.warns(UnsafeCacheBackendWarning):

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
    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK

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
    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert response.status_code == HTTPStatus.OK

    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    freezer.tick(delta=_RATE / _ATTEMPTS)

    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_leaky_bucket_full_drain(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """After full duration the bucket is empty again."""
    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert response.status_code == HTTPStatus.OK

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
    with pytest.warns(UnsafeCacheBackendWarning):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                SyncThrottle(1, rate, algorithm=LeakyBucket()),
            ]

            def get(self) -> str:
                return 'ok'

    request = dmr_rf.get('/whatever/')
    response = _Controller.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    request = dmr_rf.get('/whatever/')
    response = _Controller.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    freezer.tick(delta=int(rate))

    request = dmr_rf.get('/whatever/')
    response = _Controller.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


def test_leaky_bucket_per_endpoint_isolation(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Different endpoints have separate buckets."""
    with pytest.warns(UnsafeCacheBackendWarning):

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

    request = dmr_rf.get('/whatever/')
    response = _TwoEndpointsController.as_view()(request)
    assert response.status_code == HTTPStatus.OK

    request = dmr_rf.get('/whatever/')
    response = _TwoEndpointsController.as_view()(request)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    request = dmr_rf.put('/whatever/')
    response = _TwoEndpointsController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    request = dmr_rf.put('/whatever/')
    response = _TwoEndpointsController.as_view()(request)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


_ODD_ATTEMPTS: Final = 3


@pytest.mark.asyncio
async def test_leaky_bucket_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Async controllers work with the leaky bucket algorithm."""
    with pytest.warns(UnsafeCacheBackendWarning):

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

    for _ in range(_ODD_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK

    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers == {
        'RateLimit-Policy': '3;w=10;name="RemoteAddr", 30;w=60;name="min"',
        'RateLimit': '"RemoteAddr";r=0;t=4',
        'Content-Type': 'application/json',
    }

    freezer.tick(delta=4)

    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK

    freezer.tick(delta=_RATE)

    for _ in range(_ODD_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK

    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers == {
        'RateLimit-Policy': '3;w=10;name="RemoteAddr", 30;w=60;name="min"',
        'RateLimit': '"RemoteAddr";r=0;t=4',
        'Content-Type': 'application/json',
    }
