import json
from http import HTTPStatus

import pytest
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.endpoint import request_endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import default_renderer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from tests.infra.xml_format import XmlRenderer


class _SyncController(Controller[PydanticSerializer]):
    @modify(
        throttling=[SyncThrottle(1, Rate.second)],
        renderers=(XmlRenderer(), default_renderer),
    )
    def get(self) -> str:
        raise NotImplementedError


def test_throttle_before_negotiation(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that throttle runs before response negotiation."""
    # This will fail with an 406 error:
    request = dmr_rf.get('/whatever/', headers={'Accept': 'wrong'})
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert (
        request_endpoint(request, strict=True)
        is _SyncController.api_endpoints['GET']
    )

    # This will fail with 429:
    request = dmr_rf.get('/whatever/', headers={'Accept': 'wrong'})
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })
    assert (
        request_endpoint(request, strict=True)
        is _SyncController.api_endpoints['GET']
    )


class _AsyncController(Controller[PydanticSerializer]):
    @modify(
        throttling=[AsyncThrottle(1, Rate.second)],
        renderers=(XmlRenderer(), default_renderer),
    )
    async def get(self) -> str:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_throttle_before_negotiation_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Ensures that throttle runs before response negotiation."""
    # This will fail with an 406 error:
    request = dmr_async_rf.get('/whatever/', headers={'Accept': 'wrong'})
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert (
        request_endpoint(request, strict=True)
        is _AsyncController.api_endpoints['GET']
    )

    # This will fail with 429:
    request = dmr_async_rf.get('/whatever/', headers={'Accept': 'wrong'})
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })
    assert (
        request_endpoint(request, strict=True)
        is _AsyncController.api_endpoints['GET']
    )
