import json
from http import HTTPStatus

from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.headers import RateLimitIETFDraft, RetryAfter, XRateLimit


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
