import asyncio
import enum
import threading
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar, TypeAlias, final

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
    DjangoCacheBaseThrottleBackend,
)
from dmr.throttling.cache_keys import remote_address

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


_CacheKey: TypeAlias = Callable[
    ['Endpoint', 'Controller[BaseSerializer]'],
    str | None,
]


class _BaseThrottle(ResponseSpecProvider):
    header_prefix: ClassVar[str] = ''

    __slots__ = (
        '_algorithm',
        '_async_lock',
        '_backend',
        '_cache_key',
        '_duration_in_seconds',
        '_max_requests',
        '_sync_lock',
    )

    def __init__(
        self,
        max_requests: int,
        rate: Rate | int,
        *,
        cache_key: _CacheKey | None = None,
        number_of_proxies: int | None = None,
        backend: BaseThrottleBackend | None = None,
        algorithm: BaseThrottleAlgorithm | None = None,
    ) -> None:
        self._max_requests = max_requests
        self._duration_in_seconds = rate
        # Default implementations of the logical parts:
        self._cache_key = cache_key or remote_address
        self._backend = backend or DjangoCacheBaseThrottleBackend()
        self._algorithm = algorithm or SimpleRate()
        # Locks:
        self._sync_lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def get_cache_key(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> str | None:
        cache_key = self._cache_key(endpoint, controller)
        if cache_key is None:
            return None

        metadata = endpoint.metadata
        backend_name = type(self._backend).__qualname__
        algorith_name = type(self._algorithm).__qualname__
        cache_key_name = getattr(self._cache_key, '__qualname__', '')
        return (
            f'{metadata.operation_id}_{metadata.method}_'
            f'{backend_name}_{algorith_name}_'
            f'{self._max_requests}_{self._duration_in_seconds}_'
            f'{cache_key_name}_{cache_key}'
        )

    def headers(self, remaining: int, reset: int) -> dict[str, str]:
        prefix = self.header_prefix
        return {
            f'{prefix}RateLimit-Limit': str(self._max_requests),
            f'{prefix}RateLimit-Remaining': str(remaining),
            f'{prefix}RateLimit-Reset': str(reset),
        }

    @override
    @classmethod
    def provide_response_specs(
        cls,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when throttle triggers."""
        return cls._add_new_response(
            ResponseSpec(
                controller_cls.error_model,
                status_code=TooManyRequestsError.status_code,
                headers=cls.headers_spec(),
                description='Raised when throttling rate was hit',
            ),
            existing_responses,
        )

    @classmethod
    def headers_spec(cls) -> dict[str, HeaderSpec]:
        return {
            f'{cls.header_prefix}RateLimit-Limit': HeaderSpec(
                description=(
                    'The maximum number of requests permitted '
                    'in the current time window'
                ),
            ),
            f'{cls.header_prefix}RateLimit-Remaining': HeaderSpec(
                description=(
                    'The number of requests remaining '
                    'in the current time window'
                ),
            ),
            f'{cls.header_prefix}RateLimit-Reset': HeaderSpec(
                description=(
                    'The number of seconds until the current '
                    'rate limit window resets'
                ),
            ),
        }


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
        cache_key = self.get_cache_key(
            endpoint,
            controller,
        )
        if cache_key is None:
            return
        self.check(cache_key, controller)

    def check(
        self,
        cache_key: str,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        with self._sync_lock:
            cache_object = self._algorithm.access(
                self,
                self._backend.get(cache_key, controller),
                self._max_requests,
                int(self._duration_in_seconds),
            )
            self._backend.set(
                cache_key,
                self._algorithm.record(cache_object),
                controller,
                ttl_seconds=self._duration_in_seconds,
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
        cache_key = self.get_cache_key(
            endpoint,
            controller,
        )
        if cache_key is None:
            return
        await self.check(cache_key, controller)

    async def check(
        self,
        cache_key: str,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        async with self._async_lock:
            cache_object = self._algorithm.access(
                self,
                await self._backend.aget(cache_key, controller),
                self._max_requests,
                int(self._duration_in_seconds),
            )
            await self._backend.aset(
                cache_key,
                self._algorithm.record(cache_object),
                controller,
                ttl_seconds=self._duration_in_seconds,
            )
