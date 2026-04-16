import abc
import dataclasses
from typing import TYPE_CHECKING

from django.core.cache import DEFAULT_CACHE_ALIAS, BaseCache, caches
from typing_extensions import TypedDict, override

from dmr.settings import default_parser, default_renderer

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class CachedRateLimit(TypedDict):
    """Representation of a cached object's metadata."""

    # We usually store `int(time.time())` result here:
    time: int
    # We overly complicate the storage a bit, because this design
    # allows future potential algorithms to store requests as lists,
    # if it is needed.
    history: list[int]


class BaseThrottleBackend:
    """
    Base class for all throttling backends.

    It must provide sync and async API for sync and async throttling classes.
    """

    __slots__ = ()

    @abc.abstractmethod
    def get(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> CachedRateLimit | None:
        """Sync get the cached rate limit state."""
        raise NotImplementedError

    @abc.abstractmethod
    async def aget(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> CachedRateLimit | None:
        """Async get the cached rate limit state."""
        raise NotImplementedError

    @abc.abstractmethod
    def set(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
        cache_object: CachedRateLimit,
        *,
        ttl_seconds: int,
    ) -> None:
        """Sync set the cached rate limit state."""
        raise NotImplementedError

    @abc.abstractmethod
    async def aset(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
        cache_object: CachedRateLimit,
        *,
        ttl_seconds: int,
    ) -> None:
        """Async set the cached rate limit state."""
        raise NotImplementedError


@dataclasses.dataclass(slots=True, frozen=True)
class DjangoCache(BaseThrottleBackend):
    """
    Uses Django cache framework for storing the rate limiting state.

    .. seealso::

        https://docs.djangoproject.com/en/stable/topics/cache/

    """

    cache_name: str = DEFAULT_CACHE_ALIAS
    _cache: BaseCache = dataclasses.field(init=False)

    def __post_init__(
        self,
    ) -> None:
        """Initialize the cache backend."""
        object.__setattr__(self, '_cache', caches[self.cache_name])

    @override
    def get(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> CachedRateLimit | None:
        """Sync get the cached rate limit state."""
        stored_cache = self._cache.get(cache_key)
        return self._load_cache(controller, stored_cache)

    @override
    async def aget(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> CachedRateLimit | None:
        """Async get the cached rate limit state."""
        stored_cache = await self._cache.aget(cache_key)
        return self._load_cache(controller, stored_cache)

    @override
    def set(
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

    @override
    async def aset(
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
