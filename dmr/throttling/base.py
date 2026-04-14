import asyncio
import dataclasses
import enum
import threading
from collections import defaultdict
from collections.abc import Iterable, Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, final

from typing_extensions import override

from dmr.exceptions import TooManyRequestsError
from dmr.headers import HeaderSpec
from dmr.internal.endpoint import request_endpoint
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.throttling.algorithms import BaseThrottleAlgorithm, SimpleRate
from dmr.throttling.backends import BaseThrottleBackend, DjangoCache
from dmr.throttling.cache_keys import BaseThrottleCacheKey, RemoteAddr
from dmr.throttling.headers import (
    BaseResponseHeadersProvider,
    RetryAfter,
    XRateLimit,
)

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


@final
@enum.unique
class Rate(enum.IntEnum):
    """
    Throttling rates in seconds.

    Attributes:
        second: 1 second.
        minute: 60 seconds.
        hour: 60 * 60 seconds.
        day: 24 * 60 * 60 seconds.

    """

    second = 1
    minute = 60 * second
    hour = 60 * minute
    day = 24 * hour


class _BaseThrottle(ResponseSpecProvider):
    __slots__ = (
        '_algorithm',
        '_async_lock',
        '_backend',
        '_response_headers',
        '_sync_lock',
        'cache_key',
        'duration_in_seconds',
        'max_requests',
    )

    def __init__(
        self,
        max_requests: int,
        duration_in_seconds: Rate | int,
        *,
        cache_key: BaseThrottleCacheKey | None = None,
        backend: BaseThrottleBackend | None = None,
        algorithm: BaseThrottleAlgorithm | None = None,
        response_headers: Iterable[BaseResponseHeadersProvider] | None = None,
    ) -> None:
        """
        Creates new throttling instance.

        Parameters:
            max_requests: Maximum number of requests for the time window.
            duration_in_seconds: Time window in seconds.
            cache_key: Cache key to use.
                Defaults to :class:`~dmr.throttling.cache_keys.RemoteAddr`.
            backend: Storage backend to use.
                Defaults to :class:`~dmr.throttling.backends.DjangoCache`.
            algorithm: Algorithm to use.
                Defaults to :class:`~dmr.throttling.algorithms.SimpleRate`.
            response_headers: Iterable of response headers to use.
                Defaults to a list of
                :class:`~dmr.throttling.headers.XRateLimit`
                and :class:`~dmr.throttling.headers.RetryAfter` instances.

        """
        self.max_requests = max_requests
        self.duration_in_seconds = int(duration_in_seconds)
        # Default implementations of the logical parts:
        self.cache_key = cache_key or RemoteAddr()
        self._backend = backend or DjangoCache()
        self._algorithm = algorithm or SimpleRate()
        self._response_headers = (
            [XRateLimit(), RetryAfter()]
            if response_headers is None
            else response_headers
        )
        # Locks:
        self._sync_lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def full_cache_key(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        """Get the full cache key value."""
        cache_key = self.cache_key(endpoint, controller)
        if cache_key is None:
            return None

        metadata = endpoint.metadata
        backend_name = type(self._backend).__qualname__
        algorithm_name = type(self._algorithm).__qualname__
        cache_key_name = type(self.cache_key).__qualname__
        return (
            f'{metadata.operation_id}::{metadata.method}::'
            f'{backend_name}::{algorithm_name}::'
            f'{cache_key_name}::{cache_key}::'
            f'{self.max_requests}::{self.duration_in_seconds}'
        )

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when throttle triggers."""
        return self._add_new_response(
            ResponseSpec(
                controller_cls.error_model,
                status_code=TooManyRequestsError.status_code,
                headers=self._headers_spec(),
                description='Raised when throttling rate was hit',
            ),
            existing_responses,
        )

    def collect_response_headers(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        remaining: int,
        reset: int,
        *,
        report_all: bool = False,
    ) -> dict[str, str]:
        """Collects response headers for all ``response_headers`` classes."""
        response_headers: dict[str, str] = {}
        for header_provider in self._response_headers:
            response_headers.update(
                header_provider.response_headers(
                    endpoint,
                    controller,
                    self,
                    remaining,
                    reset,
                    report_all=report_all,
                ),
            )
        return response_headers

    def _headers_spec(self) -> dict[str, HeaderSpec]:
        headers_spec: dict[str, HeaderSpec] = {}
        for header_provider in self._response_headers:
            headers_spec.update(header_provider.provide_headers_specs())
        return headers_spec


class SyncThrottle(_BaseThrottle):
    """Sync throttle type for sync endpoints."""

    __slots__ = ()

    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        """
        Put your throttle business logic here.

        Return ``None`` if throttle check passed.
        Raise :exc:`dmr.exceptions.TooManyRequestsError`
        if throttle check failed.
        Raise :exc:`dmr.response.APIError`
        if you want to change the return code, for example,
        when some data is missing or has wrong format.
        """
        cache_key = self.full_cache_key(endpoint, controller)
        if cache_key is None:
            return
        self.check(endpoint, controller, cache_key)

    def check(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> None:
        """Check whether this request has rate limiting quota left."""
        with self._sync_lock:
            cache_object = self._algorithm.access(
                endpoint,
                controller,
                self,
                self._backend.get(endpoint, controller, cache_key),
            )
            self._backend.set(
                endpoint,
                controller,
                cache_key,
                self._algorithm.record(
                    endpoint,
                    controller,
                    self,
                    cache_object,
                ),
                ttl_seconds=self.duration_in_seconds,
            )

    def report_usage(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> dict[str, str]:
        """Report throttle usage stats."""
        cache_key = self.full_cache_key(endpoint, controller)
        if cache_key is None:
            return {}
        return self._algorithm.report_usage(
            endpoint,
            controller,
            self,
            self._backend.get(endpoint, controller, cache_key),
        )


class AsyncThrottle(_BaseThrottle):
    """Async throttle type for async endpoints."""

    __slots__ = ()

    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        """
        Put your throttle business logic here.

        Return ``None`` if throttle check passed.
        Raise :exc:`dmr.exceptions.TooManyRequestsError`
        if throttle check failed.
        Raise :exc:`dmr.response.APIError`
        if you want to change the return code, for example,
        when some data is missing or has wrong format.
        """
        cache_key = self.full_cache_key(endpoint, controller)
        if cache_key is None:
            return
        await self.check(endpoint, controller, cache_key)

    async def check(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> None:
        """Check whether this request has rate limiting quota left."""
        async with self._async_lock:
            cache_object = self._algorithm.access(
                endpoint,
                controller,
                self,
                await self._backend.aget(endpoint, controller, cache_key),
            )
            await self._backend.aset(
                endpoint,
                controller,
                cache_key,
                self._algorithm.record(
                    endpoint,
                    controller,
                    self,
                    cache_object,
                ),
                ttl_seconds=self.duration_in_seconds,
            )

    async def report_usage(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> dict[str, str]:
        """Async report throttle usage stats."""
        cache_key = self.full_cache_key(endpoint, controller)
        if cache_key is None:
            return {}
        return self._algorithm.report_usage(
            endpoint,
            controller,
            self,
            await self._backend.aget(endpoint, controller, cache_key),
        )


@dataclasses.dataclass(slots=True, frozen=True)
class ThrottlingReport:
    """
    Get throttling data to be reported in response headers.

    Unlike :exc:`dmr.exceptions.TooManyRequestsError`,
    which reports the first stat for throttle that is failing,
    it reports all stats for all throttles.

    It will make N (which is the number of throttles) requests to cache.

    .. warning::

        This class does not handle exceptions at all.
        Because we don't know how to report headers
        for failing cache connections.
        If you want to handle errors, catch them explicitly.

    """

    controller: 'Controller[BaseSerializer]'

    def report(self) -> dict[str, str]:
        """
        Report throttling all headers for a sync controller and endpoint.

        Note that it will make N consecutive requests to cache.
        It might be rather long. Use the sync version with care.
        """
        endpoint = self._get_endpoint()
        if not endpoint.metadata.throttling:
            return {}

        result_headers: defaultdict[str, list[str]] = defaultdict(list)
        for throttle in endpoint.metadata.throttling:
            # for mypy: we are sure that it is sync now
            assert isinstance(throttle, SyncThrottle)  # noqa: S101
            for header_name, header_value in throttle.report_usage(
                endpoint,
                self.controller,
            ).items():
                result_headers[header_name].append(header_value)
        return self._format_headers(result_headers)

    async def areport(self) -> dict[str, str]:
        """
        Report throttling all headers for a async controller and endpoint.

        Unlike sync version it makes parallel requests to cache
        by utilizing :func:`asyncio.gather` function inside.
        """
        endpoint = self._get_endpoint()
        if not endpoint.metadata.throttling:
            return {}

        result_headers: defaultdict[str, list[str]] = defaultdict(list)

        # We can run all tasks in "parallel":
        for report in await asyncio.gather(*[
            throttle.report_usage(endpoint, self.controller)
            for throttle in endpoint.metadata.throttling
            if isinstance(throttle, AsyncThrottle)
        ]):
            for header_name, header_value in report.items():
                result_headers[header_name].append(header_value)
        return self._format_headers(result_headers)

    def _get_endpoint(self) -> 'Endpoint':
        return request_endpoint(self.controller.request, strict=True)

    def _format_headers(
        self,
        headers: defaultdict[str, list[str]],
    ) -> dict[str, str]:
        return {
            header_name: ', '.join(header_value)
            for header_name, header_value in headers.items()
        }
