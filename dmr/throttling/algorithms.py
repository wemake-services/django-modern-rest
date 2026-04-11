import abc
import time
from typing import TYPE_CHECKING

from typing_extensions import override

from dmr.exceptions import TooManyRequestsError
from dmr.throttling.backends import CachedRateLimit

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer
    from dmr.throttling import AsyncThrottle, SyncThrottle


class BaseThrottleAlgorithm:
    __slots__ = ()

    @abc.abstractmethod
    def access(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> CachedRateLimit: ...

    @abc.abstractmethod
    def record(self, cache_object: CachedRateLimit) -> CachedRateLimit: ...


class SimpleRate(BaseThrottleAlgorithm):
    __slots__ = ()

    @override
    def access(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> CachedRateLimit:
        now = int(time.time())
        if cache_object is None or cache_object['reset'] <= now:
            # For this algorithm we use a single history
            # item which is the number of calls:
            return {'history': [0], 'reset': now + throttle.duration_in_seconds}

        requests = cache_object['history'][0]
        if requests >= throttle.max_requests:
            raise TooManyRequestsError(
                headers=throttle.collect_response_headers(
                    endpoint,
                    controller,
                    remaining=throttle.max_requests - requests,
                    reset=cache_object['reset'] - now,
                ),
            )
        return cache_object

    @override
    def record(self, cache_object: CachedRateLimit) -> CachedRateLimit:
        cache_object['history'][0] += 1
        return cache_object
