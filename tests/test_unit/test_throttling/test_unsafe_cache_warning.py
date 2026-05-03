import warnings
from collections.abc import Generator
from types import MappingProxyType
from typing import Final

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from dmr.internal.cache import clear_settings_cache
from dmr.throttling.backends._cache_safety import (
    check_throttle_cache_safety,
    clear_safety_checks,
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
def _reset_settings_cache() -> Generator[None, None, None]:
    """Reset DMR settings cache and safety checks before/after each test."""
    clear_settings_cache()
    clear_safety_checks()
    yield
    clear_settings_cache()
    clear_safety_checks()


@override_settings(CACHES=LOCMEM_CACHES, DMR_SETTINGS={})
def test_raises_by_default_with_locmem() -> None:
    """ImproperlyConfigured is raised for LocMemCache by default."""
    with pytest.raises(
        ImproperlyConfigured,
        match='allow_unsafe_throttle_cache',
    ):
        check_throttle_cache_safety('default')


@override_settings(CACHES=DUMMY_CACHES, DMR_SETTINGS={})
def test_raises_by_default_with_dummy() -> None:
    """ImproperlyConfigured is raised for DummyCache by default."""
    with pytest.raises(
        ImproperlyConfigured,
        match='allow_unsafe_throttle_cache',
    ):
        check_throttle_cache_safety('default')


@override_settings(
    CACHES=LOCMEM_CACHES,
    DMR_SETTINGS={'allow_unsafe_throttle_cache': True},
)
def test_warns_when_allow_unsafe_with_locmem() -> None:
    """Warning is emitted when allow_unsafe_throttle_cache=True."""
    with pytest.warns(UserWarning, match='not safe for production'):
        check_throttle_cache_safety('default')


@override_settings(
    CACHES=DUMMY_CACHES,
    DMR_SETTINGS={'allow_unsafe_throttle_cache': True},
)
def test_warns_when_allow_unsafe_with_dummy() -> None:
    """Warning is emitted when allow_unsafe_throttle_cache=True."""
    with pytest.warns(UserWarning, match='not safe for production'):
        check_throttle_cache_safety('default')


@override_settings(
    CACHES=REDIS_CACHES,
    DMR_SETTINGS={'allow_unsafe_throttle_cache': True},
)
def test_no_warning_for_safe_backend() -> None:
    """No warning or error for safe backends like Redis."""
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter('always')
        check_throttle_cache_safety('default')
    assert len(record) == 0


@override_settings(CACHES=REDIS_CACHES, DMR_SETTINGS={})
def test_no_error_for_safe_backend_default() -> None:
    """No error for safe backends with default settings."""
    check_throttle_cache_safety('default')
