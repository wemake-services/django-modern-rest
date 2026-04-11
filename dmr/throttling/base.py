import asyncio
import enum
import threading
from collections.abc import Iterable, Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Literal, final, overload

from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import TooManyRequestsError
from dmr.headers import HeaderSpec
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.throttling.algorithms import (
    BaseThrottleAlgorithm,
    SimpleRate,
)
from dmr.throttling.backends import (
    BaseThrottleBackend,
    DjangoCache,
)
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
        durantion_in_seconds: Rate | int,
        *,
        cache_key: BaseThrottleCacheKey | None = None,
        backend: BaseThrottleBackend | None = None,
        algorithm: BaseThrottleAlgorithm | None = None,
        response_headers: Iterable[BaseResponseHeadersProvider] | None = None,
    ) -> None:
        self.max_requests = max_requests
        self.duration_in_seconds = int(durantion_in_seconds)
        # Default implementations of the logical parts:
        self.cache_key = cache_key or RemoteAddr()
        self._backend = backend or DjangoCache()
        self._algorithm = algorithm or SimpleRate()
        self._response_headers = (
            [XRateLimit(), RetryAfter()] if response_headers is None else []
        )
        # Locks:
        self._sync_lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def get_cache_key(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        cache_key = self.cache_key(endpoint, controller)
        if cache_key is None:
            return None

        metadata = endpoint.metadata
        backend_name = type(self._backend).__qualname__
        algorith_name = type(self._algorithm).__qualname__
        cache_key_name = type(self.cache_key).__qualname__
        return (
            f'{metadata.operation_id}::{metadata.method}::'
            f'{backend_name}::{algorith_name}::'
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
    ) -> dict[str, str]:
        response_headers = {}
        for header_provider in self._response_headers:
            response_headers.update(
                header_provider.response_headers(
                    endpoint,
                    controller,
                    self,
                    remaining,
                    reset,
                ),
            )
        return response_headers

    def _headers_spec(self) -> dict[str, HeaderSpec]:
        headers_spec = {}
        for header_provider in self._response_headers:
            headers_spec.update(header_provider.provide_headers_specs())
        return headers_spec


class SyncThrottle(_BaseThrottle):
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
        cache_key = self.get_cache_key(endpoint, controller)
        if cache_key is None:
            return
        self.check(endpoint, controller, cache_key)

    def check(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> None:
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
                self._algorithm.record(cache_object),
                ttl_seconds=self.duration_in_seconds,
            )


class AsyncThrottle(_BaseThrottle):
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
        cache_key = self.get_cache_key(endpoint, controller)
        if cache_key is None:
            return
        await self.check(endpoint, controller, cache_key)

    async def check(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> None:
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
                self._algorithm.record(cache_object),
                ttl_seconds=self.duration_in_seconds,
            )


@overload
def request_throttling(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> tuple[SyncThrottle | AsyncThrottle, ...]: ...


@overload
def request_throttling(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> tuple[SyncThrottle | AsyncThrottle, ...] | None: ...


def request_throttling(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> tuple[SyncThrottle | AsyncThrottle, ...] | None:
    """
    Return the tuple of throttling instances that were for this request.

    When *strict* is passed and *request* has no throttling,
    we raise :exc:`AttributeError`.
    """
    throttling = getattr(request, '__dmr_throttling__', None)
    if throttling is None and strict:
        raise AttributeError('__dmr_throttling__')
    return throttling
