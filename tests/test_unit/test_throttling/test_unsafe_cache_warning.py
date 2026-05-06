import warnings
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, Final

import pytest
from django.conf import LazySettings
from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.settings import Settings
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.backends.django_cache import (
    AsyncDjangoCache,
    SyncDjangoCache,
    UnsafeCacheBackendWarning,
)

_LOCMEM_CACHES: Final = MappingProxyType({
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
})
_DUMMY_CACHES: Final = MappingProxyType({
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
})
_REDIS_CACHES: Final = MappingProxyType({
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://localhost:6379',
    },
})


@pytest.mark.parametrize('backend', [_LOCMEM_CACHES, _DUMMY_CACHES])
def test_unsafe_cache_raises(
    settings: LazySettings,
    *,
    backend: dict[str, Any],
) -> None:
    """Test that unsafe cache raises."""
    settings.DMR_SETTINGS = {
        **settings.DMR_SETTINGS,
        Settings.throttling_allow_unsafe_cache: False,
    }
    settings.CACHES = dict(backend)

    with pytest.raises(
        EndpointMetadataError,
        match='not safe for production',
    ):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                SyncThrottle(10, Rate.minute, backend=SyncDjangoCache()),
            ]

            def get(self) -> str:
                raise NotImplementedError


@pytest.mark.parametrize('backend', [_LOCMEM_CACHES, _DUMMY_CACHES])
def test_unsafe_cache_warns(
    settings: LazySettings,
    *,
    backend: dict[str, Any],
) -> None:
    """Test that unsafe cache warns."""
    settings.DMR_SETTINGS = {}
    settings.CACHES = dict(backend)

    with pytest.warns(
        UnsafeCacheBackendWarning,
        match='not safe for production',
    ):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling_allow_unsafe_cache = True
            throttling = [
                AsyncThrottle(10, Rate.minute, backend=AsyncDjangoCache()),
            ]

            async def get(self) -> str:
                raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.throttling_allow_unsafe_cache is True


@pytest.mark.parametrize(
    'backend',
    [_LOCMEM_CACHES, _DUMMY_CACHES, _REDIS_CACHES],
)
def test_unsafe_cache_disabled(
    settings: LazySettings,
    *,
    backend: dict[str, Any],
) -> None:
    """Test that unsafe cache can be disabled."""
    settings.DMR_SETTINGS = {}
    settings.CACHES = dict(backend)

    with warnings.catch_warnings(record=True) as captured:

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                AsyncThrottle(10, Rate.minute, backend=AsyncDjangoCache()),
            ]

            @modify(throttling_allow_unsafe_cache=None)
            async def get(self) -> str:
                raise NotImplementedError

            @validate(
                ResponseSpec(str, status_code=HTTPStatus.OK),
                throttling_allow_unsafe_cache=None,
            )
            async def post(self) -> HttpResponse:
                raise NotImplementedError

    assert len(captured) == 0
    endpoints = _Controller.api_endpoints
    assert endpoints['GET'].metadata.throttling_allow_unsafe_cache is None
    assert endpoints['POST'].metadata.throttling_allow_unsafe_cache is None


@pytest.mark.parametrize(
    'backend',
    [_REDIS_CACHES],
)
def test_safe_cache(
    settings: LazySettings,
    *,
    backend: dict[str, Any],
) -> None:
    """Test that unsafe cache can be disabled."""
    settings.DMR_SETTINGS = {}
    settings.CACHES = dict(backend)

    with warnings.catch_warnings(record=True) as captured:

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                AsyncThrottle(10, Rate.minute, backend=AsyncDjangoCache()),
            ]

            async def get(self) -> str:
                raise NotImplementedError

    assert len(captured) == 0
    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.throttling_allow_unsafe_cache
