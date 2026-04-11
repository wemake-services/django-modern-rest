import abc
from typing import TYPE_CHECKING

from django.core.cache import DEFAULT_CACHE_ALIAS, caches
from typing_extensions import TypedDict, override

from dmr.settings import default_parser, default_renderer

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class CachedRateLimit(TypedDict):
    """Representation of a cached object's metadata."""

    reset: int
    history: list[int]


class BaseThrottleBackend:
    __slots__ = ()

    @abc.abstractmethod
    def get(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> CachedRateLimit | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def aget(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> CachedRateLimit | None:
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
        raise NotImplementedError


class DjangoCache(BaseThrottleBackend):
    __slots__ = ('_cache',)

    def __init__(self, cache_name: str = DEFAULT_CACHE_ALIAS) -> None:
        self._cache = caches[cache_name]

    @override
    def get(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> CachedRateLimit | None:
        stored_cache = self._cache.get(cache_key)
        return self._load_cache(controller, stored_cache)

    @override
    async def aget(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        cache_key: str,
    ) -> CachedRateLimit | None:
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
