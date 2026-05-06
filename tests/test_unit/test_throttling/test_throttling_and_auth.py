import json
from http import HTTPStatus
from typing import Final

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft

_ATTEMPTS: Final = 5


class _BeforeAuthController(Controller[PydanticSerializer]):
    @modify(
        throttling=[SyncThrottle(1, Rate.second)],
        auth=[DjangoSessionSyncAuth()],
    )
    def get(self) -> str:
        raise NotImplementedError


def test_throttle_before_auth(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that throttle runs before auth."""
    # This will fail with an auth error:
    request = dmr_rf.get('/whatever/')
    response = _BeforeAuthController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content

    # This will fail:
    request = dmr_rf.get('/whatever/')
    response = _BeforeAuthController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })


class _AfterAuthController(Controller[PydanticSerializer]):
    @modify(
        throttling=[
            SyncThrottle(
                1,
                Rate.second,
                cache_key=RemoteAddr(runs_before_auth=False),
            ),
        ],
        auth=[DjangoSessionSyncAuth()],
    )
    def get(self) -> str:
        raise NotImplementedError


def test_throttle_after_auth(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that throttle runs after auth."""
    # No throttling:
    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _AfterAuthController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


class _AsyncBothController(Controller[PydanticSerializer]):
    throttling = [
        AsyncThrottle(
            1,
            Rate.second,
            response_headers=[RateLimitIETFDraft()],
        ),
        AsyncThrottle(
            1,
            Rate.minute,
            cache_key=RemoteAddr(runs_before_auth=False, name='per-minute'),
            response_headers=[RateLimitIETFDraft()],
        ),
    ]

    auth = [DjangoSessionAsyncAuth()]

    async def get(self) -> str:
        return 'inside'


async def _resolve(user: User) -> User:
    return user


@pytest.mark.asyncio
async def test_throttle_async_and_auth(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that async controllers work with throttling."""
    metadata = _AsyncBothController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth
    assert metadata.throttling_after_auth
    assert (
        metadata.throttling
        == metadata.throttling_before_auth + metadata.throttling_after_auth
    )

    # This will trigger first `1/s` response:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content

    # This will fail the `1/s` throttle:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"RemoteAddr";r=0;t=1'

    # Now, go forward a second and clear `1/s` rule:
    freezer.tick(delta=1)

    # Now, provide auth and make a request, it will trigger `1/m`:
    request = dmr_async_rf.get('/whatever/')
    request.auser = lambda: _resolve(User())
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.headers

    # The same request will fail `1/s` rule again:
    request = dmr_async_rf.get('/whatever/')
    request.auser = lambda: _resolve(User())
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"RemoteAddr";r=0;t=1'

    # Now, go forward a second and clear `1/s` rule:
    freezer.tick(delta=1)

    # This will now fail due to `1/m` rule:
    request = dmr_async_rf.get('/whatever/')
    request.auser = lambda: _resolve(User())
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"per-minute";r=0;t=59'


class _SyncBothController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(
            1,
            Rate.second,
            response_headers=[RateLimitIETFDraft()],
        ),
        SyncThrottle(
            1,
            Rate.minute,
            cache_key=RemoteAddr(runs_before_auth=False, name='per-minute'),
            response_headers=[RateLimitIETFDraft()],
        ),
    ]

    auth = [DjangoSessionSyncAuth()]

    def get(self) -> str:
        return 'inside'


def test_throttle_sync_before_auth(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that async controllers work with throttling."""
    metadata = _SyncBothController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth
    assert metadata.throttling_after_auth
    assert (
        metadata.throttling
        == metadata.throttling_before_auth + metadata.throttling_after_auth
    )

    # This will trigger first `1/s` response:
    request = dmr_rf.get('/whatever/')
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content

    # This will fail the `1/s` throttle:
    request = dmr_rf.get('/whatever/')
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"RemoteAddr";r=0;t=1'

    # Now, go forward a second and clear `1/s` rule:
    freezer.tick(delta=1)

    # Now, provide auth and make a request, it will trigger `1/m`:
    request = dmr_rf.get('/whatever/')
    request.user = User()
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.headers

    # The same request will fail `1/s` rule again:
    request = dmr_rf.get('/whatever/')
    request.user = User()
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"RemoteAddr";r=0;t=1'

    # Now, go forward a second and clear `1/s` rule:
    freezer.tick(delta=1)

    # This will now fail due to `1/m` rule:
    request = dmr_rf.get('/whatever/')
    request.user = User()
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"per-minute";r=0;t=59'
