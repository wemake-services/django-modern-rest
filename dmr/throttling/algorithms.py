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


# TODO: This file is pure logic. Maybe compile it?


class BaseThrottleAlgorithm:
    """Base class for all throttling algorithms."""

    __slots__ = ()

    @abc.abstractmethod
    def access(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> CachedRateLimit:
        """
        Called when new access attempt is made.

        Returns:
            Cached rate limiting state.

        Raises:
            dmr.exceptions.TooManyRequestsError: when the limit is overused.

        """
        raise NotImplementedError

    @abc.abstractmethod
    def record(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit,
    ) -> CachedRateLimit:
        """Records successful access."""
        raise NotImplementedError

    @abc.abstractmethod
    def report_usage(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> dict[str, str]:
        """Reports the throttling usage, but does not additionally increment."""
        raise NotImplementedError


class SimpleRate(BaseThrottleAlgorithm):
    """
    Simple rate algorithm.

    Defines a fixed window with a fixed amount of requests possible.
    When window is expired, resets the count of requests.
    """

    __slots__ = ()

    @override
    def access(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> CachedRateLimit:
        """Check access."""
        cache_object, now = self._process_cache(throttle, cache_object)
        if cache_object['history'][0] >= throttle.max_requests:
            raise TooManyRequestsError(
                headers=self._report_usage(
                    endpoint,
                    controller,
                    throttle,
                    cache_object,
                    now,
                ),
            )
        return cache_object

    @override
    def record(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit,
    ) -> CachedRateLimit:
        """Record successful access."""
        cache_object['history'][0] += 1
        return cache_object

    @override
    def report_usage(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> dict[str, str]:
        """Reports the throttling usage, but does not additionally increment."""
        cache_object, now = self._process_cache(throttle, cache_object)
        return self._report_usage(
            endpoint,
            controller,
            throttle,
            cache_object,
            now,
            report_all=False,
        )

    def _process_cache(
        self,
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> tuple[CachedRateLimit, int]:
        now = int(time.time())
        if cache_object is None or cache_object['time'] <= now:
            # For this algorithm we use a single history
            # item which is the number of calls:
            return (
                CachedRateLimit(
                    history=[0],
                    time=now + throttle.duration_in_seconds,
                ),
                now,
            )

        return cache_object, now

    def _report_usage(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit,
        now: int,
        *,
        report_all: bool = True,
    ) -> dict[str, str]:
        return throttle.collect_response_headers(
            endpoint,
            controller,
            remaining=throttle.max_requests - cache_object['history'][0],
            reset=cache_object['time'] - now,
            report_all=report_all,
        )


class LeakyBucket(BaseThrottleAlgorithm):
    """
    Leaky bucket algorithm.

    Requests fill the bucket; tokens leak at a steady rate.
    Unlike :class:`dmr.throttling.algorithms.SimpleRate`,
    which resets after a fixed window, ``LeakyBucket`` drains
    continuously providing smoother rate-limiting
    without allowing bursts at window boundaries.

    Internally, the bucket request level is stored in scaled units
    as ``level * duration`` so all arithmetic stays integer-only.
    Each request adds ``duration`` scaled units to the level.
    Every elapsed second ``max_requests`` scaled units leak out.
    """

    __slots__ = ()

    @override
    def access(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> CachedRateLimit:
        """Check access; raise when the bucket is full."""
        cache_object = self._process_cache(throttle, cache_object)
        if cache_object['history'][0] >= (
            throttle.max_requests * throttle.duration_in_seconds
        ):
            raise TooManyRequestsError(
                headers=self._report_usage(
                    endpoint,
                    controller,
                    throttle,
                    cache_object,
                    cache_object['time'],
                ),
            )
        return cache_object

    @override
    def record(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit,
    ) -> CachedRateLimit:
        """Record access by adding request to the bucket."""
        # One scaled unit of a request:
        cache_object['history'][0] += throttle.duration_in_seconds
        return cache_object

    @override
    def report_usage(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> dict[str, str]:
        """Report throttling usage without incrementing."""
        cache_object = self._process_cache(throttle, cache_object)
        return self._report_usage(
            endpoint,
            controller,
            throttle,
            cache_object,
            cache_object['time'],
            report_all=False,
        )

    def _process_cache(
        self,
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit | None,
    ) -> CachedRateLimit:
        now = int(time.time())
        if cache_object is None:
            return CachedRateLimit(history=[0], time=now)
        elapsed = now - cache_object['time']
        level = max(
            0,
            # Scaled level:
            cache_object['history'][0] - elapsed * throttle.max_requests,
        )
        return CachedRateLimit(history=[level], time=now)

    def _report_usage(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle | AsyncThrottle',
        cache_object: CachedRateLimit,
        now: int,
        *,
        report_all: bool = True,
    ) -> dict[str, str]:
        scaled_units = throttle.max_requests * throttle.duration_in_seconds
        remaining = (
            scaled_units - cache_object['history'][0]
        ) // throttle.duration_in_seconds
        reset = self._ceil_div(
            throttle.duration_in_seconds,
            throttle.max_requests,
        )
        return throttle.collect_response_headers(
            endpoint,
            controller,
            remaining=remaining,
            reset=reset,
            report_all=report_all,
        )

    def _ceil_div(self, dividend: int, divisor: int) -> int:
        """Integer ceiling division for non-negative values."""
        return (dividend + divisor - 1) // divisor
