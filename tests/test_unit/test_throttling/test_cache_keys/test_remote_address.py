import json
from http import HTTPStatus
from typing import Final

import pytest
from django.http import HttpResponse

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.cache_keys import remote_address

_ATTEMPTS: Final = 5


def _fake_remote_address(
    endpoint: 'Endpoint',
    controller: 'Controller[BaseSerializer]',
) -> str | None:
    assert controller.request.META.pop('REMOTE_ADDR') == '127.0.0.1'
    return remote_address(endpoint, controller)


class _SyncController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(1, Rate.second, cache_key=_fake_remote_address),
    ]

    def get(self) -> str:
        return 'inside'


def test_throttle_no_remote_address(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that `None` disables the cache key."""
    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.content
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == 'inside'


class _AsyncController(Controller[PydanticSerializer]):
    throttling = [
        AsyncThrottle(1, Rate.second, cache_key=_fake_remote_address),
    ]

    async def get(self) -> str:
        return 'inside'


@pytest.mark.asyncio
async def test_throttle_no_remote_address_async(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that `None` disables the cache key in async."""
    for _ in range(_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.content
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == 'inside'
