import abc
import dataclasses
from typing import TYPE_CHECKING

from django.core.cache import DEFAULT_CACHE_ALIAS, caches
from typing_extensions import override

from dmr.settings import default_parser, default_renderer

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(slots=True, frozen=True)
class CachedLimit:
    """Representation of a cached object's metadata."""

    reset: int
    history: list[int]


class ThrottleBackend:
    __slots__ = ()

    @abc.abstractmethod
    def get(
        self,
        cache_key: str,
        controller: 'Controller[BaseSerializer]',
    ) -> CachedLimit | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def aget(
        self,
        cache_key: str,
        controller: 'Controller[BaseSerializer]',
    ) -> CachedLimit | None:
        raise NotImplementedError

    @abc.abstractmethod
    def set(
        self,
        cache_key: str,
        cache_object: CachedLimit,
        controller: 'Controller[BaseSerializer]',
        *,
        ttl_seconds: int,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def aset(
        self,
        cache_key: str,
        cache_object: CachedLimit,
        controller: 'Controller[BaseSerializer]',
        *,
        ttl_seconds: int,
    ) -> None:
        raise NotImplementedError


class DjangoCacheThrottleBackend(ThrottleBackend):
    __slots__ = ('_cache',)

    def __init__(self, cache_name: str = DEFAULT_CACHE_ALIAS) -> None:
        self._cache = caches[cache_name]

    @override
    def get(
        self,
        cache_key: str,
        controller: 'Controller[BaseSerializer]',
    ) -> CachedLimit | None:
        stored_cache = self._cache.get(cache_key)
        return self._load_cache(stored_cache, controller)

    @override
    async def aget(
        self,
        cache_key: str,
        controller: 'Controller[BaseSerializer]',
    ) -> CachedLimit | None:
        stored_cache = await self._cache.aget(cache_key)
        return self._load_cache(stored_cache, controller)

    @override
    def set(
        self,
        cache_key: str,
        cache_object: CachedLimit,
        controller: 'Controller[BaseSerializer]',
        *,
        ttl_seconds: int,
    ) -> None:
        self._cache.set(
            cache_key,
            self._dump_cache(cache_object, controller),
            timeout=ttl_seconds,
        )

    @override
    async def aset(
        self,
        cache_key: str,
        cache_object: CachedLimit,
        controller: 'Controller[BaseSerializer]',
        *,
        ttl_seconds: int,
    ) -> None:
        await self._cache.aset(
            cache_key,
            self._dump_cache(cache_object, controller),
            timeout=ttl_seconds,
        )

    def _load_cache(
        self,
        stored_cache: bytes | None,
        controller: 'Controller[BaseSerializer]',
    ) -> CachedLimit | None:
        if stored_cache is None:
            return None

        return controller.serializer.from_python(  # type: ignore[no-any-return]
            controller.serializer.deserialize(
                stored_cache,
                parser=default_parser,
                request=controller.request,
                model=CachedLimit,
            ),
            model=CachedLimit,
            strict=None,
        )

    def _dump_cache(
        self,
        cache_object: CachedLimit,
        controller: 'Controller[BaseSerializer]',
    ) -> bytes:
        return controller.serializer.serialize(
            cache_object,
            renderer=default_renderer,
        )
