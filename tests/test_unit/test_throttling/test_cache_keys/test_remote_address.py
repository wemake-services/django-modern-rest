import json
from http import HTTPStatus
from typing import Final

import pytest
from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle, ThrottlingReport
from dmr.throttling.cache_keys import RemoteAddr

_ATTEMPTS: Final = 5


class _FakeRemoteAddr(RemoteAddr):
    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        assert controller.request.META.pop('REMOTE_ADDR', None) in {
            '127.0.0.1',
            None,
        }
        return super().__call__(endpoint, controller)


class _SyncController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(1, Rate.second, cache_key=_FakeRemoteAddr()),
    ]

    def get(self) -> str:
        assert ThrottlingReport(self).report() == {}
        return 'inside'


def test_throttle_no_limits(
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
        AsyncThrottle(1, Rate.second, cache_key=_FakeRemoteAddr()),
    ]

    async def get(self) -> str:
        assert await ThrottlingReport(self).areport() == {}
        return 'inside'


@pytest.mark.asyncio
async def test_throttle_no_limits_async(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that `None` disables the cache key in async."""
    metadata = _AsyncController.api_endpoints['GET'].metadata
    assert metadata.throttling == metadata.throttling_before_auth

    for _ in range(_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))  # noqa: WPS476
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.content
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == 'inside'
