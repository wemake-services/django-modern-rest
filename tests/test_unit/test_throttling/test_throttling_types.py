import copy
import sys
from typing import Any

import pytest

from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.algorithms import LeakyBucket, SimpleRate
from dmr.throttling.backends import AsyncDjangoCache, SyncDjangoCache
from dmr.throttling.cache_keys import RemoteAddr
from dmr.throttling.headers import RateLimitIETFDraft


@pytest.mark.parametrize('throttle_cls', [SyncThrottle, AsyncThrottle])
def test_throttle_replace(
    throttle_cls: type[SyncThrottle | AsyncThrottle],
) -> None:
    """`replace` overrides the given fields and keeps the rest."""
    original = throttle_cls(1000, Rate.minute)

    # Override every field:
    copied = original.replace(
        max_requests=1,
        duration_in_seconds=Rate.hour,
        cache_key=RemoteAddr(runs_before_auth=False),
        backend=(
            SyncDjangoCache()  # type: ignore[arg-type]
            if isinstance(original, SyncThrottle)
            else AsyncDjangoCache()
        ),
        algorithm=LeakyBucket(),
        response_headers=[RateLimitIETFDraft()],
    )

    assert type(copied) is throttle_cls  # noqa: WPS516
    assert copied is not original
    assert copied.max_requests == 1
    assert copied.duration_in_seconds == Rate.hour
    assert copied.cache_key.runs_before_auth is False
    assert original.max_requests != copied.max_requests


@pytest.mark.parametrize('throttle_cls', [SyncThrottle, AsyncThrottle])
def test_throttle_replace_empty(
    throttle_cls: type[SyncThrottle | AsyncThrottle],
) -> None:
    """`replace` overrides the given fields and keeps the rest."""
    original = throttle_cls(1000, Rate.minute)

    # No arguments -> an equivalent copy:
    copied = original.replace()

    assert type(copied) is throttle_cls  # noqa: WPS516
    assert copied is not original
    assert copied.max_requests == original.max_requests
    assert copied.duration_in_seconds == original.duration_in_seconds


@pytest.mark.skipif(
    sys.version_info < (3, 13),
    reason='`copy.replace` is added in Python 3.13',
)
@pytest.mark.parametrize('throttle_cls', [SyncThrottle, AsyncThrottle])
def test_throttle_copy_replace(
    throttle_cls: type[SyncThrottle | AsyncThrottle],
) -> None:
    """`copy.replace` works through the `__replace__` alias."""
    # This is a hack to work around `copy.replace` typing:
    original: Any = throttle_cls(1000, Rate.minute)

    if sys.version_info >= (3, 13):
        # `typeshed` wants `__replace__(**kwargs: Any)`, our alias is stricter:
        copied = copy.replace(original, max_requests=2, algorithm=LeakyBucket())

        assert type(copied) is throttle_cls  # noqa: WPS516
        assert copied is not original
        assert copied.max_requests == 2
        assert copied.duration_in_seconds == original.duration_in_seconds
        assert isinstance(copied._algorithm, LeakyBucket)

    # Original does not change:
    assert original.max_requests == 1000
    assert isinstance(original._algorithm, SimpleRate)
