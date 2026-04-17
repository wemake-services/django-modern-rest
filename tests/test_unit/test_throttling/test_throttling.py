import json
from http import HTTPMethod, HTTPStatus
from typing import Final, TypeAlias

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot

from dmr import Controller, ResponseSpec, modify, validate
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle

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


@pytest.mark.parametrize('method', [HTTPMethod.GET, HTTPMethod.PUT])
@pytest.mark.parametrize('serializer', serializers)
def test_throttle_sync_per_endpoint(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    serializer: type[BaseSerializer],
    method: HTTPMethod,
) -> None:
    """Ensures sync per endpoint throttle."""

    class _SyncEndpointController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        @modify(throttling=[SyncThrottle(1, Rate.second)])
        def get(self) -> str:
            return 'inside'

        @validate(
            ResponseSpec(str, status_code=HTTPStatus.OK),
            throttling=[SyncThrottle(1, Rate.second)],
        )
        def put(self) -> HttpResponse:
            return self.to_response('inside')

    metadata = _SyncEndpointController.api_endpoints[str(method)].metadata
    assert metadata.throttling_before_auth
    assert len(metadata.throttling_before_auth) == 1
    assert metadata.throttling_after_auth is None
    assert HTTPStatus.TOO_MANY_REQUESTS in metadata.responses

    for _ in range(_ATTEMPTS):
        freezer.tick(delta=1)  # seconds
        request = dmr_rf.generic(str(method), '/whatever/')
        response = _SyncEndpointController.as_view()(request)
        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.OK, response.content
        assert response.headers == {'Content-Type': 'application/json'}
        assert json.loads(response.content) == 'inside'

    # This will fail:
    request = dmr_rf.generic(str(method), '/whatever/')
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

    # However, you can still call another method:
    request = dmr_rf.generic(
        'PUT' if method == HTTPMethod.GET else 'GET',
        '/whatever/',
    )
    response = _SyncEndpointController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'inside'


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_throttle_async_per_controller(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that async controllers work with throttling."""

    class _AsyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        throttling = [AsyncThrottle(1, Rate.second)]

        async def get(self) -> str:
            return 'inside'

        async def put(self) -> str:
            return 'inside'

    metadata = _AsyncController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth
    assert len(metadata.throttling_before_auth) == 1
    assert metadata.throttling_after_auth is None
    assert HTTPStatus.TOO_MANY_REQUESTS in metadata.responses

    for _ in range(_ATTEMPTS):
        freezer.tick(delta=1)  # seconds
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))  # noqa: WPS476
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
async def test_throttle_settings_override(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
) -> None:
    """Ensures that async throttling from settings work."""
    settings.DMR_SETTINGS = {
        Settings.throttling: [AsyncThrottle(1, Rate.second)],
    }

    class _DisabledPerController(Controller[PydanticSerializer]):
        throttling = None

        async def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledPerController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is None
    assert metadata.throttling_after_auth is None

    class _DisabledPerEndpoint(Controller[PydanticSerializer]):
        throttling = [
            AsyncThrottle(10, Rate.minute),
            AsyncThrottle(10, Rate.hour),
        ]

        @modify(throttling=None)
        async def get(self) -> str:
            raise NotImplementedError

    metadata = _DisabledPerEndpoint.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is None
    assert metadata.throttling_after_auth is None


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_throttle_async_per_settings(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that async throttling from settings work."""
    settings.DMR_SETTINGS = {
        Settings.throttling: [AsyncThrottle(_ATTEMPTS, Rate.second)],
    }

    class _AsyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        async def get(self) -> str:
            return 'inside'

        async def put(self) -> str:
            return 'inside'

    for _ in range(_ATTEMPTS):
        request = dmr_async_rf.get('/whatever/')
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))  # noqa: WPS476
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


@pytest.mark.parametrize('serializer', serializers)
def test_throttle_sync_multiple_sources(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that sync throttling from settings work."""
    settings.DMR_SETTINGS = {
        Settings.throttling: [SyncThrottle(_ATTEMPTS, Rate.second)],
    }

    class _SyncController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        throttling = [
            SyncThrottle(10, Rate.minute),
            SyncThrottle(10, Rate.hour),
        ]

        def get(self) -> str:
            return 'inside'

    metadata = _SyncController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth
    assert len(metadata.throttling_before_auth) == 3
    assert metadata.throttling_after_auth is None
    assert HTTPStatus.TOO_MANY_REQUESTS in metadata.responses

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


@pytest.mark.parametrize(
    'rate',
    [Rate.second, Rate.minute, Rate.hour, Rate.day],
)
def test_throttle_sync_rates(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    rate: Rate,
) -> None:
    """Ensures that rates work correctly."""

    class _SyncController(Controller[PydanticSerializer]):
        throttling = [SyncThrottle(1, rate)]

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
