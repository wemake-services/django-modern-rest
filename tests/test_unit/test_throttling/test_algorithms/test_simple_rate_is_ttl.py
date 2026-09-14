from typing import Final

from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.algorithms import SimpleRate
from dmr.throttling.backends.base import CachedRateLimit

_MAX_REQUESTS: Final = 5
_WINDOW: Final = Rate.minute
_DUMMY_NOW: Final = 999_999
_EXPIRE_AT_NOW: Final = 70


def test_ttl_reset_uses_ttl_directly() -> None:
    """TTL mode: reset equals ttl directly, no time subtraction.

    When the backend sets ``is_ttl=True``, ``time`` holds the remaining
    seconds from Redis ``TTL``. The algorithm should use it directly
    for the ``reset`` header without subtracting the current time.
    """
    algorithm = SimpleRate()
    throttle = SyncThrottle(_MAX_REQUESTS, _WINDOW, algorithm=algorithm)

    cache_object: CachedRateLimit = {
        'history': [2],
        'time': 45,
        'is_ttl': True,
    }
    headers = algorithm._report_usage(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        throttle,
        cache_object,
        now=_DUMMY_NOW,
    )

    assert headers['X-RateLimit-Reset'] == str(cache_object['time'])
    assert headers['X-RateLimit-Remaining'] == str(
        _MAX_REQUESTS - cache_object['history'][0],
    )


def test_expire_at_subtracts_now() -> None:
    """Expire_at mode: reset = time - now.

    When ``is_ttl`` is not set, ``time`` holds an absolute ``expire_at``
    timestamp. The algorithm subtracts the current time to get remaining
    seconds for the ``reset`` header.
    """
    algorithm = SimpleRate()
    throttle = SyncThrottle(_MAX_REQUESTS, _WINDOW, algorithm=algorithm)

    cache_object: CachedRateLimit = {
        'history': [1],
        'time': 100,
    }
    headers = algorithm._report_usage(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        throttle,
        cache_object,
        now=_EXPIRE_AT_NOW,
    )

    assert headers['X-RateLimit-Reset'] == str(
        cache_object['time'] - _EXPIRE_AT_NOW,
    )
    assert headers['X-RateLimit-Remaining'] == str(
        _MAX_REQUESTS - cache_object['history'][0],
    )


def test_ttl_skips_window_expiry() -> None:
    """TTL mode: _process_cache does not reset the window.

    When ``is_ttl=True``, window expiry is managed by the backend
    (e.g. Redis key TTL), so ``_process_cache`` must not reset
    even if ``time`` is small.
    """
    algorithm = SimpleRate()
    throttle = SyncThrottle(_MAX_REQUESTS, _WINDOW, algorithm=algorithm)

    cache_object: CachedRateLimit = {
        'history': [3],
        'time': 1,
        'is_ttl': True,
    }
    cached, _now = algorithm._process_cache(throttle, cache_object)

    assert cached is cache_object
    assert cached['history'] == [3]
    assert cached['time'] == 1


def test_expire_at_resets_expired_window() -> None:
    """Expire_at mode: _process_cache resets when window expired.

    When ``is_ttl`` is not set and ``time <= now``, the window has
    expired and ``_process_cache`` creates a fresh cache object.
    """
    algorithm = SimpleRate()
    throttle = SyncThrottle(_MAX_REQUESTS, _WINDOW, algorithm=algorithm)

    cache_object: CachedRateLimit = {
        'history': [3],
        'time': 1,
    }
    cached, now = algorithm._process_cache(throttle, cache_object)

    assert cached['history'] == [0]
    assert cached['time'] == now + 60
    assert 'is_ttl' not in cached
