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
from dmr.throttling.backends.django_cache import UnsafeCacheBackendWarning
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft

_ATTEMPTS: Final = 5


def test_throttle_before_auth(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that throttle runs before auth."""
    with pytest.warns(UnsafeCacheBackendWarning):

        class _BeforeAuthController(Controller[PydanticSerializer]):
            @modify(
                throttling=[SyncThrottle(1, Rate.second)],
                auth=[DjangoSessionSyncAuth()],
            )
            def get(self) -> str:
                raise NotImplementedError

    request = dmr_rf.get('/whatever/')
    response = _BeforeAuthController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content

    request = dmr_rf.get('/whatever/')
    response = _BeforeAuthController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })


def test_throttle_after_auth(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that throttle runs after auth."""
    with pytest.warns(UnsafeCacheBackendWarning):

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

    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _AfterAuthController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


async def _resolve(user: User) -> User:
    return user


@pytest.mark.asyncio
async def test_throttle_async_and_auth(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that async controllers work with throttling."""
    with pytest.warns(UnsafeCacheBackendWarning):

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
                    cache_key=RemoteAddr(
                        runs_before_auth=False,
                        name='per-minute',
                    ),
                    response_headers=[RateLimitIETFDraft()],
                ),
            ]

            auth = [DjangoSessionAsyncAuth()]

            async def get(self) -> str:
                return 'inside'

    metadata = _AsyncBothController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth
    assert metadata.throttling_after_auth
    assert (
        metadata.throttling
        == metadata.throttling_before_auth + metadata.throttling_after_auth
    )

    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content

    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"RemoteAddr";r=0;t=1'

    freezer.tick(delta=1)

    request = dmr_async_rf.get('/whatever/')
    request.auser = lambda: _resolve(User())
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.headers

    request = dmr_async_rf.get('/whatever/')
    request.auser = lambda: _resolve(User())
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"RemoteAddr";r=0;t=1'

    freezer.tick(delta=1)

    request = dmr_async_rf.get('/whatever/')
    request.auser = lambda: _resolve(User())
    response = await dmr_async_rf.wrap(_AsyncBothController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"per-minute";r=0;t=59'


def test_throttle_sync_before_auth(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that sync controllers work with throttling."""
    with pytest.warns(UnsafeCacheBackendWarning):

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
                    cache_key=RemoteAddr(
                        runs_before_auth=False,
                        name='per-minute',
                    ),
                    response_headers=[RateLimitIETFDraft()],
                ),
            ]

            auth = [DjangoSessionSyncAuth()]

            def get(self) -> str:
                return 'inside'

    metadata = _SyncBothController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth
    assert metadata.throttling_after_auth
    assert (
        metadata.throttling
        == metadata.throttling_before_auth + metadata.throttling_after_auth
    )

    request = dmr_rf.get('/whatever/')
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content

    request = dmr_rf.get('/whatever/')
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"RemoteAddr";r=0;t=1'

    freezer.tick(delta=1)

    request = dmr_rf.get('/whatever/')
    request.user = User()
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.headers

    request = dmr_rf.get('/whatever/')
    request.user = User()
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"RemoteAddr";r=0;t=1'

    freezer.tick(delta=1)

    request = dmr_rf.get('/whatever/')
    request.user = User()
    response = _SyncBothController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers['RateLimit'] == '"per-minute";r=0;t=59'
