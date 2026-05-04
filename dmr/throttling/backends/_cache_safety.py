import warnings
from typing import Final

from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured


class UnsafeCacheBackendWarning(UserWarning):
    """Warning emitted when an unsafe cache backend is used for throttling."""


_UNSAFE_CACHE_BACKENDS: Final = frozenset((
    'django.core.cache.backends.locmem.LocMemCache',
    'django.core.cache.backends.dummy.DummyCache',
))

_WARNING_MSG: Final = (
    "Throttling is using '{backend}' cache backend which is not safe for "
    'production: counters are NOT shared between processes/instances. '
    'Use Redis or Memcached instead.'
)

_ERROR_MSG: Final = (
    _WARNING_MSG
    + ' To suppress this error and run at your own risk, set '
    + "'allow_unsafe_throttle_cache': True in DMR_SETTINGS."
)


def check_throttle_cache_safety(cache_name: str) -> None:
    cache = caches[cache_name]
    backend = f'{type(cache).__module__}.{type(cache).__qualname__}'

    if backend not in _UNSAFE_CACHE_BACKENDS:
        return

    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    allow_unsafe = resolve_setting(Settings.allow_unsafe_throttle_cache)
    if allow_unsafe:
        warnings.warn(  # noqa: B028
            _WARNING_MSG.format(backend=backend),
            category=UnsafeCacheBackendWarning,
        )
    else:
        raise ImproperlyConfigured(_ERROR_MSG.format(backend=backend))
