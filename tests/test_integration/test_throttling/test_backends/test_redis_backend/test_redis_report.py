import json
from http import HTTPStatus
from typing import Any, Final

import pytest
import redis
from dirty_equals import IsOneOf
from django.http import HttpResponse
from redis import asyncio as aioredis

from dmr import Controller, ResponseSpec, validate
from dmr.endpoint import request_endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle, ThrottlingReport
from dmr.throttling.algorithms import LeakyBucket
from dmr.throttling.backends import AsyncDjangoCache, SyncDjangoCache
from dmr.throttling.backends.redis import AsyncRedis, SyncRedis
from dmr.throttling.headers import RateLimitIETFDraft, XRateLimit

_draft_headers: Final = RateLimitIETFDraft()
_ratelimit_headers: Final = XRateLimit()


def test_throttle_multiple_headers(
    dmr_rf: DMRRequestFactory,
    redis_client: 'redis.Redis[Any]',
) -> None:
    """Ensures that throttle information can be served on success."""

    class _ReportsController(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                str,
                status_code=HTTPStatus.OK,
                headers={
                    **_draft_headers.provide_headers_specs(),
                    **_ratelimit_headers.provide_headers_specs(),
                },
            ),
            throttling=[
                SyncThrottle(
                    1,
                    Rate.minute,
                    response_headers=[_draft_headers],
                    backend=SyncRedis(redis_client),
                ),
                SyncThrottle(
                    5,
                    Rate.hour,
                    response_headers=[_ratelimit_headers],
                    backend=SyncRedis(redis_client),
                ),
            ],
        )
        def get(self) -> HttpResponse:
            return self.to_response(
                'inside',
                headers=ThrottlingReport(self).report(),
            )

    request = dmr_rf.get('/whatever/')

    response = _ReportsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '"RemoteAddr";q=1;w=60',
        'RateLimit': IsOneOf('"RemoteAddr";r=0;t=60', '"RemoteAddr";r=0;t=59'),
        'X-RateLimit-Limit': '5',
        'X-RateLimit-Remaining': '4',
        'X-RateLimit-Reset': IsOneOf('3600', '3599'),
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


@pytest.mark.parametrize(
    'backend_cls',
    [
        SyncDjangoCache,
        SyncRedis,
    ],
)
def test_throttle_sync_leaky_bucket(
    dmr_rf: DMRRequestFactory,
    redis_client: 'redis.Redis[Any]',
    *,
    backend_cls: type[SyncDjangoCache | SyncRedis],
) -> None:
    """Ensures that throttle information can be served on success."""

    class _Controller(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                str,
                status_code=HTTPStatus.OK,
                headers=_draft_headers.provide_headers_specs(),
            ),
            throttling=[
                SyncThrottle(
                    2,
                    Rate.minute,
                    response_headers=[_draft_headers],
                    backend=(
                        backend_cls(redis_client)
                        if issubclass(backend_cls, SyncRedis)
                        else backend_cls(allow_unsafe_cache=True)
                    ),
                    algorithm=LeakyBucket(),
                ),
            ],
        )
        def get(self) -> HttpResponse:
            return self.to_response(
                'inside',
                headers=ThrottlingReport(self).report(),
            )

    request = dmr_rf.get('/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '"RemoteAddr";q=2;w=60',
        'RateLimit': IsOneOf('"RemoteAddr";r=1;t=30', '"RemoteAddr";r=1;t=29'),
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


@pytest.mark.parametrize(
    'backend_cls',
    [
        SyncDjangoCache,
        SyncRedis,
    ],
)
def test_throttle_sync_leaky_bucket_limit_reached(
    dmr_rf: DMRRequestFactory,
    redis_client: 'redis.Redis[Any]',
    *,
    backend_cls: type[SyncDjangoCache | SyncRedis],
) -> None:
    """Ensures that throttle information can be served on limit."""

    class _Controller(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                str,
                status_code=HTTPStatus.OK,
                headers=_draft_headers.provide_headers_specs(),
            ),
            throttling=[
                SyncThrottle(
                    1,
                    Rate.hour,
                    response_headers=[_draft_headers],
                    backend=(
                        backend_cls(redis_client)
                        if issubclass(backend_cls, SyncRedis)
                        else backend_cls(allow_unsafe_cache=True)
                    ),
                    algorithm=LeakyBucket(),
                ),
            ],
        )
        def get(self) -> HttpResponse:
            return self.to_response(
                'inside',
                headers=ThrottlingReport(self).report(),
            )

    request = dmr_rf.get('/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '"RemoteAddr";q=1;w=3600',
        'RateLimit': IsOneOf(
            '"RemoteAddr";r=0;t=3600',
            '"RemoteAddr";r=0;t=3599',
        ),
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


@pytest.mark.asyncio
async def test_throttle_multiple_headers_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    redis_async_client: 'aioredis.Redis[Any]',
) -> None:
    """Ensures that throttle information can be served on success."""

    class _AsyncReportsController(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                str,
                status_code=HTTPStatus.OK,
                headers={
                    **_draft_headers.provide_headers_specs(),
                    **_ratelimit_headers.provide_headers_specs(),
                },
            ),
            throttling=[
                AsyncThrottle(
                    1,
                    Rate.minute,
                    response_headers=[_draft_headers],
                    backend=AsyncRedis(redis_async_client),
                ),
                AsyncThrottle(
                    5,
                    Rate.hour,
                    response_headers=[_ratelimit_headers],
                    backend=AsyncRedis(redis_async_client),
                ),
            ],
        )
        async def get(self) -> HttpResponse:
            return self.to_response(
                'inside',
                headers=await ThrottlingReport(self).areport(),
            )

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncReportsController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'RateLimit-Policy': '"RemoteAddr";q=1;w=60',
        'RateLimit': IsOneOf('"RemoteAddr";r=0;t=60', '"RemoteAddr";r=0;t=59'),
        'X-RateLimit-Limit': '5',
        'X-RateLimit-Remaining': '4',
        'X-RateLimit-Reset': IsOneOf('3600', '3599'),
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == 'inside'


@pytest.mark.parametrize(
    'backend_cls',
    [
        SyncDjangoCache,
        SyncRedis,
    ],
)
def test_throttle_report_no_state(
    dmr_rf: DMRRequestFactory,
    redis_client: 'redis.Redis[Any]',
    *,
    backend_cls: type[SyncDjangoCache | SyncRedis],
) -> None:
    """Ensures that a throttle with no stored state reports a full window."""
    throttle = SyncThrottle(
        5,
        Rate.hour,
        response_headers=[_ratelimit_headers],
        backend=(
            backend_cls(redis_client)
            if issubclass(backend_cls, SyncRedis)
            else backend_cls(allow_unsafe_cache=True)
        ),
    )

    class _Controller(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                str,
                status_code=HTTPStatus.OK,
                headers=_ratelimit_headers.provide_headers_specs(),
            ),
        )
        def get(self) -> HttpResponse:
            return self.to_response(
                'inside',
                headers=throttle.report_usage(
                    request_endpoint(self.request, strict=True),
                    self,
                ),
            )

    request = dmr_rf.get('/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'X-RateLimit-Limit': '5',
        'X-RateLimit-Remaining': '5',
        'X-RateLimit-Reset': '3600',
        'Content-Type': 'application/json',
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'backend_cls',
    [
        AsyncDjangoCache,
        AsyncRedis,
    ],
)
async def test_throttle_report_no_state_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    redis_async_client: 'aioredis.Redis[Any]',
    *,
    backend_cls: type[AsyncDjangoCache | AsyncRedis],
) -> None:
    """Ensures that a throttle with no stored state reports a full window."""
    throttle = AsyncThrottle(
        5,
        Rate.hour,
        response_headers=[_ratelimit_headers],
        backend=(
            backend_cls(redis_async_client)
            if issubclass(backend_cls, AsyncRedis)
            else backend_cls(allow_unsafe_cache=True)
        ),
    )

    class _AsyncController(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                str,
                status_code=HTTPStatus.OK,
                headers=_ratelimit_headers.provide_headers_specs(),
            ),
        )
        async def get(self) -> HttpResponse:
            return self.to_response(
                'inside',
                headers=await throttle.report_usage(
                    request_endpoint(self.request, strict=True),
                    self,
                ),
            )

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {
        'X-RateLimit-Limit': '5',
        'X-RateLimit-Remaining': '5',
        'X-RateLimit-Reset': '3600',
        'Content-Type': 'application/json',
    }
