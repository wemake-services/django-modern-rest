import json
from http import HTTPMethod, HTTPStatus
from typing import Final, TypeAlias

import pytest
from django.conf import LazySettings
from django.core.cache import cache
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, ResponseSpec, modify, validate
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()


class _XSyncThrottle(SyncThrottle):
    header_prefix = 'X-'


class _SyncEndpointController(Controller[PydanticSerializer]):
    @modify(throttling=[_XSyncThrottle((1, Rate.second))])
    def get(self) -> str:
        return 'inside'


def test_throttle_sync_per_endpoint(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures custom throttle prefix."""
    # First will pass:
    request = dmr_rf.get('/whatever/')
    response = _SyncEndpointController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    # This will fail:
    request = dmr_rf.get('/whatever/')
    response = _SyncEndpointController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {
        'X-RateLimit-Limit': '1',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': '1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })

class _XAsyncThrottle(AsyncThrottle):
    header_prefix = 'X-'


class _AsyncController(Controller[PydanticSerializer],):
    throttling = [_XAsyncThrottle((1, Rate.second))]

    async def get(self) -> str:
        return 'inside'



@pytest.mark.asyncio
async def test_throttle_async_per_endpoint(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures custom throttle prefix async."""
    # This will pass:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    # This wiil fail:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {
        'X-RateLimit-Limit': '1',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': '1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })
