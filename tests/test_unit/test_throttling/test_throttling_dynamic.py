import json
from http import HTTPStatus
from typing import Final, TypeAlias

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import (
    AsyncThrottle,
    Rate,
    SyncOrAsyncThrottle,
    SyncThrottle,
)

_Serializes: TypeAlias = list[type[BaseSerializer]]
serializers: Final[_Serializes] = [
    PydanticSerializer,
    PydanticFastSerializer,
]

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass  # noqa: WPS420
else:  # pragma: no cover
    serializers.append(MsgspecSerializer)


_ATTEMPTS: Final = 5
_THROTTLE: Final = SyncOrAsyncThrottle(
    SyncThrottle(_ATTEMPTS, Rate.second),
    AsyncThrottle(_ATTEMPTS, Rate.second),
)


@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.filterwarnings(
    'ignore::dmr.throttling.backends.django_cache.UnsafeCacheBackendWarning',
)
def test_sync_or_async_throttle_settings_sync(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures SyncOrAsyncThrottle in settings resolves and rate-limits sync."""
    settings.DMR_SETTINGS = {Settings.throttling: [_THROTTLE]}

    class _SyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        def get(self) -> str:
            return 'inside'

        def put(self) -> str:
            return 'inside'

    metadata = _SyncController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is not None
    assert isinstance(metadata.throttling_before_auth[0], SyncThrottle)

    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.content
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == 'inside'

    # This will now fail:
    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {
        'X-RateLimit-Limit': '5',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': '1',
        'Retry-After': '1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })

    # But, `PUT` is fine:
    request = dmr_rf.put('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.filterwarnings(
    'ignore::dmr.throttling.backends.django_cache.UnsafeCacheBackendWarning',
)
async def test_sync_or_async_throttle_settings_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures SyncOrAsyncThrottle in settings resolves and rate-limits async.

    Uses async controller.
    """
    settings.DMR_SETTINGS = {Settings.throttling: [_THROTTLE]}

    class _AsyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> str:
            return 'inside'

        async def put(self) -> str:
            return 'inside'

    metadata = _AsyncController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is not None
    assert isinstance(metadata.throttling_before_auth[0], AsyncThrottle)

    for _ in range(_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(
            _AsyncController.as_view()(request),  # noqa: WPS476
        )
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.content
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == 'inside'

    # This will now fail:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.content
    )
    assert response.headers == {
        'X-RateLimit-Limit': '5',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': '1',
        'Retry-After': '1',
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })

    # But, `PUT` is fine:
    request = dmr_async_rf.put('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'
