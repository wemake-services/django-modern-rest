import json
from http import HTTPStatus
from typing import Final, TypeAlias

import pytest
from django.conf import LazySettings
from django.core.cache import cache
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings, clear_settings_cache
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.backends.django_cache import UnsafeCacheBackendWarning

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


@pytest.mark.parametrize('serializer', serializers)
def test_throttle_sync_per_endpoint(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures per-endpoint sync throttling works per HTTP method."""
    settings.DMR_SETTINGS = {
        Settings.throttle_allow_unsafe_cache: True,
        Settings.throttling: [],
    }
    clear_settings_cache()
    cache.clear()

    with pytest.warns(UnsafeCacheBackendWarning):
        throttle_get = SyncThrottle(1, Rate.second)
    with pytest.warns(UnsafeCacheBackendWarning):
        throttle_put = SyncThrottle(1, Rate.second)

    class _SyncEndpointController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        @modify(throttling=[throttle_get])
        def get(self) -> str:
            return 'inside'

        @modify(throttling=[throttle_put])
        def put(self) -> str:
            return 'inside'

    # First GET is ok
    request = dmr_rf.get('/whatever/')
    response = _SyncEndpointController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.headers
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    # Second GET is rate limited
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

    # PUT is still fine (independent throttle)
    request = dmr_rf.put('/whatever/')
    response = _SyncEndpointController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    settings.DMR_SETTINGS = {}
    clear_settings_cache()


@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.asyncio
async def test_throttle_async_per_controller(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures async controller-level throttling limits repeated requests."""
    with pytest.warns(UnsafeCacheBackendWarning):
        throttle = AsyncThrottle(1, Rate.second)

    class _AsyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        throttling = [throttle]

        async def get(self) -> str:
            return 'inside'

        async def put(self) -> str:
            return 'inside'

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

    # But, `PUT` is still fine:
    request = dmr_async_rf.put('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_throttle_settings_override(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures throttling from settings applies when controller has none."""
    with pytest.warns(UnsafeCacheBackendWarning):
        throttle = AsyncThrottle(1, Rate.second)

    settings.DMR_SETTINGS = {
        Settings.throttling: [throttle],
    }
    clear_settings_cache()

    class _AsyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> str:
            return 'inside'

    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'
    settings.DMR_SETTINGS = {}
    clear_settings_cache()


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_throttle_async_per_settings(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures async throttling from settings limits GET, but not PUT."""
    settings.DMR_SETTINGS = {
        Settings.throttle_allow_unsafe_cache: True,
    }
    clear_settings_cache()

    with pytest.warns(UnsafeCacheBackendWarning):
        throttle = [AsyncThrottle(_ATTEMPTS, Rate.second)]

    settings.DMR_SETTINGS = {
        Settings.throttle_allow_unsafe_cache: True,
        Settings.throttling: throttle,
    }
    clear_settings_cache()

    class _AsyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> str:
            return 'inside'

        async def put(self) -> str:
            return 'inside'

    for _ in range(_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
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
    settings.DMR_SETTINGS = {}
    clear_settings_cache()


@pytest.mark.parametrize('serializer', serializers)
def test_throttle_sync_multiple_sources(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures settings and controller sync throttling are merged correctly."""
    settings.DMR_SETTINGS = {
        Settings.throttle_allow_unsafe_cache: True,
    }
    clear_settings_cache()

    with pytest.warns(UnsafeCacheBackendWarning):
        settings.DMR_SETTINGS = {
            Settings.throttle_allow_unsafe_cache: True,
            Settings.throttling: [SyncThrottle(_ATTEMPTS, Rate.second)],
        }
    clear_settings_cache()

    with pytest.warns(UnsafeCacheBackendWarning):
        minute_throttle = SyncThrottle(10, Rate.minute)
    with pytest.warns(UnsafeCacheBackendWarning):
        hour_throttle = SyncThrottle(10, Rate.hour)

    class _SyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        throttling = [minute_throttle, hour_throttle]

        def get(self) -> str:
            return 'inside'

    endpoint_metadata = _SyncController.api_endpoints['GET'].metadata
    assert endpoint_metadata.throttling_before_auth
    assert len(endpoint_metadata.throttling_before_auth) == 3
    assert endpoint_metadata.throttling_after_auth is None
    assert HTTPStatus.TOO_MANY_REQUESTS in endpoint_metadata.responses

    for _ in range(_ATTEMPTS):
        request = dmr_rf.get('/whatever/')
        response = _SyncController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.headers
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == 'inside'

    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.headers
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
    settings.DMR_SETTINGS = {}
    clear_settings_cache()


@pytest.mark.parametrize(
    'rate',
    [Rate.second, Rate.minute, Rate.hour, Rate.day],
)
def test_throttle_sync_rates(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    rate: Rate,
) -> None:
    """Ensures sync throttling respects different time window rates."""
    with pytest.warns(UnsafeCacheBackendWarning):
        throttle = SyncThrottle(1, rate)

    class _SyncController(Controller[PydanticSerializer]):
        throttling = [throttle]

        def get(self) -> str:
            return 'inside'

    # First is ok:
    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.headers
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'

    # Second is rate limited:
    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, (
        response.headers
    )
    assert response.headers == {
        'X-RateLimit-Limit': '1',
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': str(int(rate)),
        'Retry-After': str(int(rate)),
        'Content-Type': 'application/json',
    }
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Too many requests', 'type': 'ratelimit'}],
    })

    # Now, tick needed amount of seconds:
    freezer.tick(delta=int(rate))

    # It's ok again:
    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.headers
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'
