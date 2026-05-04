from types import MappingProxyType
from typing import Final

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from dmr.throttling.backends.django_cache import (
    SyncDjangoCache,
    UnsafeCacheBackendWarning,
)

LOCMEM_CACHES: Final = MappingProxyType({
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
})
DUMMY_CACHES: Final = MappingProxyType({
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
})
REDIS_CACHES: Final = MappingProxyType({
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://localhost:6379',
    },
})


@pytest.fixture(autouse=True)
def _reset_settings_cache(
    dmr_clean_settings: None,
) -> None:
    """Reset DMR settings cache."""


@override_settings(CACHES=LOCMEM_CACHES, DMR_SETTINGS={})
def test_raises_by_default_with_locmem() -> None:
    """ImproperlyConfigured is raised for LocMemCache by default."""
    with pytest.raises(
        ImproperlyConfigured,
        match='throttle_allow_unsafe_cache',
    ):
        SyncDjangoCache()


@override_settings(CACHES=DUMMY_CACHES, DMR_SETTINGS={})
def test_raises_by_default_with_dummy() -> None:
    """ImproperlyConfigured is raised for DummyCache by default."""
    with pytest.raises(
        ImproperlyConfigured,
        match='throttle_allow_unsafe_cache',
    ):
        SyncDjangoCache()


@override_settings(
    CACHES=LOCMEM_CACHES,
    DMR_SETTINGS={'throttle_allow_unsafe_cache': True},
)
def test_warns_when_allow_unsafe_with_locmem() -> None:
    """Warning is emitted when throttle_allow_unsafe_cache=True."""
    with pytest.warns(
        UnsafeCacheBackendWarning,
        match='not safe for production',
    ):
        SyncDjangoCache()


@override_settings(
    CACHES=DUMMY_CACHES,
    DMR_SETTINGS={'throttle_allow_unsafe_cache': True},
)
def test_warns_when_allow_unsafe_with_dummy() -> None:
    """Warning is emitted when throttle_allow_unsafe_cache=True."""
    with pytest.warns(
        UnsafeCacheBackendWarning,
        match='not safe for production',
    ):
        SyncDjangoCache()


@override_settings(
    CACHES=REDIS_CACHES,
    DMR_SETTINGS={'throttle_allow_unsafe_cache': True},
)
def test_no_warning_for_safe_backend() -> None:
    """No warning or error for safe backends like Redis."""
    SyncDjangoCache()


@override_settings(CACHES=REDIS_CACHES, DMR_SETTINGS={})
def test_no_error_for_safe_backend_default() -> None:
    """No error for safe backends with default settings."""
    SyncDjangoCache()
