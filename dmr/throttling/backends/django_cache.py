import dataclasses
from typing import TYPE_CHECKING

from django.core.cache import DEFAULT_CACHE_ALIAS, BaseCache, caches
from typing_extensions import override

from dmr.settings import default_parser, default_renderer
from dmr.throttling.backends.base import (
    BaseThrottleAsyncBackend,
    BaseThrottleSyncBackend,
    CachedRateLimit,
)

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer
    from dmr.throttling import AsyncThrottle, SyncThrottle
    from dmr.throttling.algorithms import BaseThrottleAlgorithm


@dataclasses.dataclass(slots=True, frozen=True)
class _DjangoCache:
    cache_name: str = DEFAULT_CACHE_ALIAS
    _cache: BaseCache = dataclasses.field(init=False)

    def __post_init__(
        self,
    ) -> None:
        """Initialize the cache backend."""
        object.__setattr__(self, '_cache', caches[self.cache_name])

    def _load_cache(
        self,
        controller: 'Controller[BaseSerializer]',
        stored_cache: bytes | None,
    ) -> CachedRateLimit | None:
        if stored_cache is None:
            return None

        return controller.serializer.deserialize(  # type: ignore[no-any-return]
            stored_cache,
            parser=default_parser,
            request=controller.request,
            model=CachedRateLimit,
        )

    def _dump_cache(
        self,
        controller: 'Controller[BaseSerializer]',
        cache_object: CachedRateLimit,
    ) -> bytes:
        return controller.serializer.serialize(
            cache_object,
            renderer=default_renderer,
        )


@dataclasses.dataclass(slots=True, frozen=True)
class SyncDjangoCache(_DjangoCache, BaseThrottleSyncBackend):
    """
    Uses Django sync cache framework for storing the rate limiting state.

    .. seealso::

        https://docs.djangoproject.com/en/stable/topics/cache/

    """

    @override
    def incr(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle',
        *,
        cache_key: str,
        algorithm: 'BaseThrottleAlgorithm',
    ) -> CachedRateLimit:
        # It is not atomic, but this is fine, we document this:
        cache_object = algorithm.access(
            endpoint,
            controller,
            throttle,
            self.get(endpoint, controller, throttle, cache_key=cache_key),
        )
        self._set(
            endpoint,
            controller,
            cache_key,
            cache_object,
            ttl_seconds=throttle.duration_in_seconds,
        )
        return cache_object

    @override
    def get(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'SyncThrottle',
        *,
        cache_key: str,
    ) -> CachedRateLimit | None:
        """Sync get the cached rate limit state."""
        stored_cache = self._cache.get(cache_key)
        return self._load_cache(controller, stored_cache)

    def _set(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
        cache_object: CachedRateLimit,
        *,
        ttl_seconds: int,
    ) -> None:
        """Sync set the cached rate limit state."""
        self._cache.set(
            cache_key,
            self._dump_cache(controller, cache_object),
            timeout=ttl_seconds,
        )


@dataclasses.dataclass(slots=True, frozen=True)
class AsyncDjangoCache(_DjangoCache, BaseThrottleAsyncBackend):
    """
    Uses Django async cache framework for storing the rate limiting state.

    .. seealso::

        https://docs.djangoproject.com/en/stable/topics/cache/

    """

    @override
    async def incr(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'AsyncThrottle',
        *,
        cache_key: str,
        algorithm: 'BaseThrottleAlgorithm',
    ) -> CachedRateLimit:
        # It is not atomic, but this is fine, we document this:
        cache_object = algorithm.access(
            endpoint,
            controller,
            throttle,
            await self.get(endpoint, controller, throttle, cache_key=cache_key),
        )
        await self._set(
            endpoint,
            controller,
            cache_key,
            cache_object,
            ttl_seconds=throttle.duration_in_seconds,
        )
        return cache_object

    @override
    async def get(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: 'AsyncThrottle',
        *,
        cache_key: str,
    ) -> CachedRateLimit | None:
        """Async get the cached rate limit state."""
        stored_cache = await self._cache.aget(cache_key)
        return self._load_cache(controller, stored_cache)

    async def _set(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
        cache_object: CachedRateLimit,
        *,
        ttl_seconds: int,
    ) -> None:
        """Async set the cached rate limit state."""
        await self._cache.aset(
            cache_key,
            self._dump_cache(controller, cache_object),
            timeout=ttl_seconds,
        )
