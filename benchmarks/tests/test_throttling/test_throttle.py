from __future__ import annotations

import asyncio
from typing import Final, Self

from pytest_codspeed import BenchmarkFixture
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security import AsyncAuth, SyncAuth
from dmr.serializer import BaseSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.algorithms import BaseThrottleAlgorithm
from dmr.throttling.backends import (
    BaseThrottleAsyncBackend,
    BaseThrottleSyncBackend,
    CachedRateLimit,
)
from dmr.throttling.cache_keys import RemoteAddr

_REPEAT: Final = 1000


class _Auth(SyncAuth):
    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self:
        return self

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        return {}

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return {}

    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        return None


class _AllowBackend(BaseThrottleSyncBackend):
    __slots__ = ()

    @override
    def incr(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        throttle: SyncThrottle,
        *,
        cache_key: str,
        algorithm: BaseThrottleAlgorithm,
    ) -> CachedRateLimit:
        return {
            'history': [0],
            'time': 0,
        }

    @override
    def get(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        throttle: SyncThrottle,
        *,
        cache_key: str,
    ) -> CachedRateLimit | None:
        return None


class _AsyncAuth(AsyncAuth):
    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self:
        return self

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        return {}

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return {}

    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        return None


class _AsyncAllowBackend(BaseThrottleAsyncBackend):
    __slots__ = ()

    @override
    async def incr(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        throttle: AsyncThrottle,
        *,
        cache_key: str,
        algorithm: BaseThrottleAlgorithm,
    ) -> CachedRateLimit:
        return {
            'history': [0],
            'time': 0,
        }

    @override
    async def get(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        throttle: AsyncThrottle,
        *,
        cache_key: str,
    ) -> CachedRateLimit | None:
        return None


class _ThrottleController(Controller[MsgspecSerializer]):
    auth = (_Auth(),)
    throttling = (
        SyncThrottle(
            1_000_000_000,
            Rate.minute,
            backend=_AllowBackend(),
        ),
        SyncThrottle(
            1_000_000_000,
            Rate.minute,
            backend=_AllowBackend(),
            cache_key=RemoteAddr(
                runs_before_auth=False,
                name='AfterAuth',
            ),
        ),
    )

    def get(self) -> None:
        return None


class _AsyncThrottleController(Controller[MsgspecSerializer]):
    auth = (_AsyncAuth(),)
    throttling = (
        AsyncThrottle(
            1_000_000_000,
            Rate.minute,
            backend=_AsyncAllowBackend(),
        ),
        AsyncThrottle(
            1_000_000_000,
            Rate.minute,
            backend=_AsyncAllowBackend(),
            cache_key=RemoteAddr(
                runs_before_auth=False,
                name='AfterAuth',
            ),
        ),
    )

    async def get(self) -> None:
        return None


def test_realistic_sync_endpoint(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark auth and throttling through dispatch."""
    request = dmr_rf.get('/test', REMOTE_ADDR='192.0.2.1')
    controller = _ThrottleController()
    controller.setup(request)

    @benchmark
    def factory() -> None:
        for _ in range(_REPEAT):
            controller.dispatch(request)


def test_realistic_async_endpoint(
    benchmark: BenchmarkFixture,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Benchmark async auth and throttling through dispatch."""
    request = dmr_async_rf.get('/test', REMOTE_ADDR='192.0.2.1')
    controller = _AsyncThrottleController()
    controller.setup(request)

    async def factory() -> None:
        for _ in range(_REPEAT):
            await dmr_async_rf.wrap(controller.dispatch(request))

    # TODO: Remove this when pytest-codspeed implements
    # async benchmarks.
    with asyncio.Runner() as runner:
        benchmark(lambda: runner.run(factory()))
