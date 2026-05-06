import json
from http import HTTPStatus

import pytest
from dirty_equals import IsStr
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle


class _SyncEndpointController(Controller[PydanticFastSerializer]):
    @modify(throttling=[SyncThrottle(1, Rate.hour)])
    def get(self) -> str:
        return 'inside'


def test_throttle_sync_real_time(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures sync per endpoint throttle."""
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
        'X-RateLimit-Reset': IsStr(),  # it might be around 3600
        'Retry-After': IsStr(),
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })


class _AsyncController(Controller[PydanticFastSerializer]):
    throttling = [AsyncThrottle(1, Rate.hour)]

    async def get(self) -> str:
        return 'inside'


@pytest.mark.asyncio
async def test_throttle_async_per_controller(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that async controllers work with throttling."""
    # First will pass:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    # Others will fail:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {
        'X-RateLimit-Limit': '1',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': IsStr(),  # it might be around 3600
        'Retry-After': IsStr(),
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })
