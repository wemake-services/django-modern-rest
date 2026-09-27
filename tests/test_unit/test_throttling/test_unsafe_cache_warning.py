import warnings
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, Final

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from typing_extensions import override

from dmr import Controller, ResponseSpec, validate
from dmr.exceptions import EndpointMetadataError
from dmr.metadata import EndpointMetadata
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.serializer import BaseSerializer
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
    settings.CACHES = dict(backend)

    with pytest.raises(
        EndpointMetadataError,
        match='not safe for production',
    ):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                SyncThrottle(
                    10,
                    Rate.minute,
                    backend=SyncDjangoCache(allow_unsafe_cache=False),
                ),
            ]

            def get(self) -> str:
                raise NotImplementedError


@pytest.mark.parametrize('backend', [_LOCMEM_CACHES, _DUMMY_CACHES])
@pytest.mark.parametrize('explicit_backend', [True, False])
def test_unsafe_cache_warns_async(
    settings: LazySettings,
    *,
    backend: dict[str, Any],
    explicit_backend: bool,
) -> None:
    """Test that unsafe cache warns by default for async controllers."""
    settings.CACHES = dict(backend)
    throttle = (
        AsyncThrottle(10, Rate.minute, backend=AsyncDjangoCache())
        if explicit_backend
        else AsyncThrottle(10, Rate.minute)
    )

    with pytest.warns(
        UnsafeCacheBackendWarning,
        match='not safe for production',
    ):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [throttle]

            async def get(self) -> str:
                raise NotImplementedError


@pytest.mark.parametrize('backend', [_LOCMEM_CACHES, _DUMMY_CACHES])
@pytest.mark.parametrize('explicit_backend', [True, False])
def test_unsafe_cache_warns_sync(
    settings: LazySettings,
    *,
    backend: dict[str, Any],
    explicit_backend: bool,
) -> None:
    """Test that unsafe cache warns by default for sync controllers."""
    settings.CACHES = dict(backend)
    throttle = (
        SyncThrottle(10, Rate.minute, backend=SyncDjangoCache())
        if explicit_backend
        else SyncThrottle(10, Rate.minute)
    )

    with pytest.warns(
        UnsafeCacheBackendWarning,
        match='not safe for production',
    ):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [throttle]

            def get(self) -> str:
                raise NotImplementedError


@pytest.mark.parametrize(
    'backend',
    [_LOCMEM_CACHES, _DUMMY_CACHES, _REDIS_CACHES],
)
def test_unsafe_cache_disabled(
    settings: LazySettings,
    *,
    backend: dict[str, Any],
) -> None:
    """Test that unsafe cache check can be disabled."""
    settings.CACHES = dict(backend)

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                AsyncThrottle(
                    10,
                    Rate.minute,
                    backend=AsyncDjangoCache(allow_unsafe_cache=None),
                ),
            ]

            async def get(self) -> str:
                raise NotImplementedError

            @validate(ResponseSpec(str, status_code=HTTPStatus.OK))
            async def post(self) -> HttpResponse:
                raise NotImplementedError

    assert not captured


def test_unsafe_cache_is_checked_per_backend(settings: LazySettings) -> None:
    """Each backend instance controls its own unsafe cache check."""
    settings.CACHES = dict(_LOCMEM_CACHES)

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                SyncThrottle(
                    10,
                    Rate.minute,
                    backend=SyncDjangoCache(allow_unsafe_cache=None),
                ),
                SyncThrottle(100, Rate.hour, backend=SyncDjangoCache()),
            ]

            def get(self) -> str:
                raise NotImplementedError

    assert len(captured) == 1
    assert captured[0].category is UnsafeCacheBackendWarning


def test_safe_cache(settings: LazySettings) -> None:
    """Test that safe cache does not warn, even in the strict mode."""
    settings.CACHES = dict(_REDIS_CACHES)

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                AsyncThrottle(
                    10,
                    Rate.minute,
                    backend=AsyncDjangoCache(allow_unsafe_cache=False),
                ),
            ]

            async def get(self) -> str:
                raise NotImplementedError

    assert not captured


class _StrictThrottle(SyncThrottle):
    @override
    def validate(
        self,
        controller_cls: type[Controller[BaseSerializer]],
        metadata: EndpointMetadata,
    ) -> None:
        raise EndpointMetadataError('Test')


def test_throttle_validate_hook_is_called() -> None:
    """Throttle.validate hook is called during endpoint validation."""
    with pytest.raises(EndpointMetadataError, match='Test'):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [_StrictThrottle(10, Rate.minute)]

            def get(self) -> str:
                raise NotImplementedError
