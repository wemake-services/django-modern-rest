import json
from http import HTTPStatus

import pytest
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.headers import RateLimitIETFDraft, RetryAfter, XRateLimit


class _SyncEndpointController(Controller[PydanticSerializer]):
    @modify(throttling=[SyncThrottle(1, Rate.second)])
    def get(self) -> str:
        return 'inside'


def test_throttle_sync_x_prefix(
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
        'Retry-After': '1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })


class _AsyncController(Controller[PydanticSerializer]):
    throttling = [AsyncThrottle(1, Rate.second)]

    async def get(self) -> str:
        return 'inside'


@pytest.mark.asyncio
async def test_throttle_async_x_prefix(
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

    # This will fail:
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
        'Retry-After': '1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })


class _SyncNoHeadersController(Controller[PydanticSerializer]):
    @modify(throttling=[SyncThrottle(1, Rate.second, response_headers=())])
    def get(self) -> str:
        return 'inside'


def test_throttle_sync_no_headers(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures custom headers rules."""
    # First will pass:
    request = dmr_rf.get('/whatever/')
    response = _SyncNoHeadersController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    # This will fail:
    request = dmr_rf.get('/whatever/')
    response = _SyncNoHeadersController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })


class _SyncAllHeadersController(Controller[PydanticSerializer]):
    @modify(
        throttling=[
            SyncThrottle(
                1,
                Rate.second,
                response_headers=[
                    RetryAfter(),
                    XRateLimit(),
                    RateLimitIETFDraft(),
                ],
            ),
        ],
    )
    def get(self) -> str:
        return 'inside'


def test_throttle_sync_all_headers(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures all header rules."""
    # First will pass:
    request = dmr_rf.get('/whatever/')
    response = _SyncAllHeadersController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    # This will fail:
    request = dmr_rf.get('/whatever/')
    response = _SyncAllHeadersController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {
        'Retry-After': '1',
        'X-RateLimit-Limit': '1',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': '1',
        'RateLimit-Policy': '1;w=1;name="RemoteAddr"',
        'RateLimit': '"RemoteAddr";r=0;t=1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })
