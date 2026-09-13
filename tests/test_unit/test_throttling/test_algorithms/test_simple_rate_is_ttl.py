from typing import Final

from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.algorithms import SimpleRate
from dmr.throttling.backends.base import CachedRateLimit

_MAX_REQUESTS: Final = 5
_WINDOW: Final = Rate.minute
_DUMMY_NOW: Final = 999_999
_EXPIRE_AT_NOW: Final = 70


def test_ttl_reset_uses_ttl_directly() -> None:
    """TTL mode: reset equals ttl directly, no time subtraction."""
    algorithm = SimpleRate()
    throttle = SyncThrottle(_MAX_REQUESTS, _WINDOW, algorithm=SimpleRate())

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
    assert headers['X-RateLimit-Reset'] == '45'
    assert headers['X-RateLimit-Remaining'] == '3'


def test_expire_at_subtracts_now() -> None:
    """Expire_at mode: reset = time - now."""
    algorithm = SimpleRate()
    throttle = SyncThrottle(_MAX_REQUESTS, _WINDOW, algorithm=SimpleRate())

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
    assert headers['X-RateLimit-Reset'] == '30'
    assert headers['X-RateLimit-Remaining'] == '4'


def test_ttl_skips_window_expiry() -> None:
    """TTL mode: _process_cache does not reset the window."""
    algorithm = SimpleRate()
    throttle = SyncThrottle(_MAX_REQUESTS, _WINDOW, algorithm=SimpleRate())

    cache_object: CachedRateLimit = {
        'history': [3],
        'time': 1,
        'is_ttl': True,
    }
    cached, _now = algorithm._process_cache(throttle, cache_object)
    assert cached.get('is_ttl') is True
    assert cached['history'] == [3]
    assert cached['time'] == 1


def test_expire_at_resets_expired_window() -> None:
    """Expire_at mode: _process_cache resets when window expired."""
    algorithm = SimpleRate()
    throttle = SyncThrottle(_MAX_REQUESTS, _WINDOW, algorithm=SimpleRate())

    cache_object: CachedRateLimit = {
        'history': [3],
        'time': 1,
    }
    cached, now = algorithm._process_cache(throttle, cache_object)
    assert cached['history'] == [0]
    assert cached['time'] == now + 60
