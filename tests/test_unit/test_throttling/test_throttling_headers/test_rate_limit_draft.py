import json
from http import HTTPStatus

from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft


class _SyncSeveralController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(5, Rate.minute, cache_key=RemoteAddr(name='test')),
    ]

    @modify(
        throttling=[
            SyncThrottle(
                1,
                Rate.second,
                response_headers=[
                    RateLimitIETFDraft(),
                ],
            ),
        ],
    )
    def get(self) -> str:
        return 'inside'


def test_throttle_multiple_specs(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures all header rules."""
    # First will pass:
    request = dmr_rf.get('/whatever/')
    response = _SyncSeveralController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    # This will fail:
    request = dmr_rf.get('/whatever/')
    response = _SyncSeveralController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {
        'RateLimit-Policy': '1;w=1;name="RemoteAddr", 5;w=60;name="test"',
        'RateLimit': '"RemoteAddr";r=0;t=1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })
