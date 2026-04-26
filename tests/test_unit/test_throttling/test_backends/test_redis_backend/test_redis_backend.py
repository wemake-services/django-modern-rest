import json
from http import HTTPStatus
from typing import Any, Final

import pytest

try:
    import redis
except ImportError:  # pragma: no cover
    pytest.skip(reason='redis is not installed', allow_module_level=True)

from dirty_equals import IsOneOf
from django.http import HttpResponse
from inline_snapshot import snapshot
from redis import asyncio as aioredis

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.algorithms import (
    LeakyBucket,
    SimpleRate,
)
from dmr.throttling.backends.redis import AsyncRedis, SyncRedis
from dmr.throttling.headers import RateLimitIETFDraft, RetryAfter

_ATTEMPTS: Final = 2
_RATE: Final = Rate.minute


def test_redis_sync_simple_rate(
    dmr_rf: DMRRequestFactory,
    redis_client: 'redis.Redis[Any]',
) -> None:
    """Ensure correct sync redis client works with simple rate."""

    class _SyncController(Controller[PydanticFastSerializer]):
        @modify(
            throttling=[
                SyncThrottle(
                    _ATTEMPTS,
                    _RATE,
                    backend=SyncRedis(redis_client),
                    algorithm=SimpleRate(),
                ),
            ],
        )
        def get(self) -> str:
            return 'inside'

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
        'Content-Type': 'application/json',
        'X-RateLimit-Limit': '2',
        'X-RateLimit-Remaining': '0',
        # Time can vary:
        'X-RateLimit-Reset': IsOneOf('60', '59'),
        'Retry-After': IsOneOf('60', '59'),
    }
    assert json.loads(response.content) == snapshot({
        'detail': [
            {'msg': 'Too many requests', 'type': 'ratelimit'},
        ],
    })


def test_redis_sync_leaky_bucket(
    dmr_rf: DMRRequestFactory,
    redis_client: 'redis.Redis[Any]',
) -> None:
    """Ensure correct sync redis client works with leaky bucket."""

    class _SyncController(Controller[PydanticFastSerializer]):
        @modify(
            throttling=[
                SyncThrottle(
                    _ATTEMPTS,
                    _RATE,
                    backend=SyncRedis(redis_client),
                    algorithm=LeakyBucket(),
                ),
            ],
        )
        def get(self) -> str:
            return 'inside'

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
        'Content-Type': 'application/json',
        'X-RateLimit-Limit': '2',
        'X-RateLimit-Remaining': '0',
        # Time can vary:
        'X-RateLimit-Reset': IsOneOf('30', '29'),
        'Retry-After': IsOneOf('30', '29'),
    }
    assert json.loads(response.content) == snapshot({
        'detail': [
            {'msg': 'Too many requests', 'type': 'ratelimit'},
        ],
    })


@pytest.mark.asyncio
async def test_redis_async_simple_rate(
    dmr_async_rf: DMRAsyncRequestFactory,
    redis_async_client: 'aioredis.Redis[Any]',
) -> None:
    """Async controllers work with redis backend and simple rate algorithm."""

    class _AsyncController(Controller[PydanticFastSerializer]):
        throttling = [
            AsyncThrottle(
                _ATTEMPTS,
                _RATE,
                algorithm=SimpleRate(),
                backend=AsyncRedis(redis_async_client),
                response_headers=[RateLimitIETFDraft(), RetryAfter()],
            ),
        ]

        async def get(self) -> str:
            return 'inside'

    # Success attempts:
    for _ in range(_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.content

    # Rejected:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers == {
        'Content-Type': 'application/json',
        'RateLimit-Policy': '2;w=60;name="RemoteAddr"',
        # Time can vary:
        'RateLimit': IsOneOf('"RemoteAddr";r=0;t=60', '"RemoteAddr";r=0;t=59'),
        'Retry-After': IsOneOf('60', '59'),
    }


@pytest.mark.asyncio
async def test_redis_async_leaky_bucket(
    dmr_async_rf: DMRAsyncRequestFactory,
    redis_async_client: 'aioredis.Redis[Any]',
) -> None:
    """Async controllers work with redis backend and leaky bucket algorithm."""

    class _AsyncController(Controller[PydanticFastSerializer]):
        throttling = [
            AsyncThrottle(
                _ATTEMPTS,
                _RATE,
                algorithm=LeakyBucket(),
                backend=AsyncRedis(redis_async_client),
                response_headers=[RateLimitIETFDraft(), RetryAfter()],
            ),
        ]

        async def get(self) -> str:
            return 'inside'

    # Success attempts:
    for _ in range(_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.content

    # Rejected:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers == {
        'Content-Type': 'application/json',
        'RateLimit-Policy': '2;w=60;name="RemoteAddr"',
        # Time can vary:
        'RateLimit': IsOneOf('"RemoteAddr";r=0;t=30', '"RemoteAddr";r=0;t=29'),
        'Retry-After': IsOneOf('30', '29'),
    }
