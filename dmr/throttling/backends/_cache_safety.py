import warnings

from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured

_UNSAFE_CACHE_BACKENDS = frozenset((
    'django.core.cache.backends.locmem.LocMemCache',
    'django.core.cache.backends.dummy.DummyCache',
))

_WARNING_MSG = (
    "Throttling is using '{backend}' cache backend which is not safe for "
    'production: counters are NOT shared between processes/instances. '
    'Use Redis or Memcached instead.'
)

_ERROR_MSG = (
    _WARNING_MSG
    + ' To suppress this error and run at your own risk, set '
    + "'allow_unsafe_throttle_cache': True in DMR_SETTINGS."
)

# Tracks which cache names have already been checked to avoid redundant
# checks on every throttling operation:
_CHECKED_CACHES: set[str] = set()


def is_cache_checked(cache_name: str) -> bool:
    """Return whether the given cache name has already been checked."""
    return cache_name in _CHECKED_CACHES


def clear_safety_checks() -> None:
    """Clear the set of checked cache names.

    Useful in tests when re-checking with different settings.
    """
    _CHECKED_CACHES.clear()


def check_throttle_cache_safety(cache_name: str) -> None:
    cache = caches[cache_name]
    backend = f'{type(cache).__module__}.{type(cache).__qualname__}'

    if backend not in _UNSAFE_CACHE_BACKENDS:
        _CHECKED_CACHES.add(cache_name)
        return

    from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

    allow_unsafe = resolve_setting(Settings.allow_unsafe_throttle_cache)
    _CHECKED_CACHES.add(cache_name)
    if allow_unsafe:
        warnings.warn(  # noqa: B028
            _WARNING_MSG.format(backend=backend),
        )
    else:
        raise ImproperlyConfigured(_ERROR_MSG.format(backend=backend))
