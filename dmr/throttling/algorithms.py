import abc
import time
from typing import TYPE_CHECKING

from typing_extensions import override

from dmr.exceptions import TooManyRequestsError
from dmr.throttling.backends import CachedLimit

if TYPE_CHECKING:
    from dmr.throttling import AsyncThrottle, SyncThrottle


class ThrottleAlgorithm:
    __slots__ = ()

    @abc.abstractmethod
    def access(
        self,
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: 'CachedLimit | None',
        max_requests: int,
        duration_in_seconds: int,
    ) -> 'CachedLimit': ...

    @abc.abstractmethod
    def record(self, cache_object: 'CachedLimit') -> 'CachedLimit': ...


class SimpleRate(ThrottleAlgorithm):
    __slots__ = ()

    @override
    def access(
        self,
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: 'CachedLimit | None',
        max_requests: int,
        duration_in_seconds: int,
    ) -> 'CachedLimit':
        now = int(time.time())
        if cache_object is None or cache_object.reset <= now:
            # For this algorithm we use a single history
            # item which is the number of calls:
            return CachedLimit(history=[0], reset=now + duration_in_seconds)

        if cache_object.history[0] >= max_requests:
            raise TooManyRequestsError(
                headers=throttle.headers(
                    remaining=max_requests - cache_object.history[0],
                    reset=cache_object.reset - now,
                ),
            )
        return cache_object

    @override
    def record(self, cache_object: 'CachedLimit') -> 'CachedLimit':
        cache_object.history[0] += 1
        return cache_object
