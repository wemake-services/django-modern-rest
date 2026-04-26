try:
    import redis  # pyright: ignore[reportUnusedImport]
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `redis` is not installed, '
        "consider using `pip install 'redis'`",
    )
    raise

import dataclasses
from typing import TYPE_CHECKING, Any, ClassVar, cast

from redis import asyncio as aioredis
from redis.commands.core import AsyncScript, Script
from typing_extensions import override

from dmr.exceptions import TooManyRequestsError
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
class SyncRedis(BaseThrottleSyncBackend):
    """
    Uses sync Redis client for multiproccess safe rate-limiting.

    .. seealso::

        https://redis.readthedocs.io

    """

    client: 'redis.Redis[Any]'
    _script: Script = dataclasses.field(init=False, repr=False, compare=False)

    needs_transaction_script: ClassVar[str] = 'lua'  # pyright: ignore[reportIncompatibleVariableOverride]

    @override
    def initialize_algorithm(self, algorithm: 'BaseThrottleAlgorithm') -> None:
        BaseThrottleSyncBackend.initialize_algorithm(self, algorithm)
        script = algorithm.transaction_script(self.needs_transaction_script)
        # for mypy: we just checked this:
        assert script is not None  # noqa: S101
        object.__setattr__(  # noqa: PLC2801
            self,
            '_script',
            self.client.register_script(script),
        )

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
        script_result = cast(
            tuple[int, int, int],
            self._script(
                keys=[cache_key],
                args=[throttle.max_requests, throttle.duration_in_seconds, 0],
            ),
        )
        cache_object = CachedRateLimit(
            history=[script_result[1]],
            time=script_result[2],
        )
        if script_result[0] == 0:
            raise TooManyRequestsError(
                headers=algorithm.report_usage(
                    endpoint,
                    controller,
                    throttle,
                    cache_object,
                ),
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
        script_result = cast(
            tuple[int, int, int],
            self._script(
                keys=[cache_key],
                # read-only request with the last `1`:
                args=[throttle.max_requests, throttle.duration_in_seconds, 1],
            ),
        )
        return CachedRateLimit(
            history=[script_result[1]],
            time=script_result[2],
        )


@dataclasses.dataclass(slots=True, frozen=True)
class AsyncRedis(BaseThrottleAsyncBackend):
    """
    Uses async Redis client for multiproccess safe rate-limiting.

    .. seealso::

        https://redis.readthedocs.io

    """

    client: 'aioredis.Redis[Any]'
    _script: AsyncScript = dataclasses.field(
        init=False,
        repr=False,
        compare=False,
    )

    needs_transaction_script: ClassVar[str] = 'lua'  # pyright: ignore[reportIncompatibleVariableOverride]

    @override
    def initialize_algorithm(self, algorithm: 'BaseThrottleAlgorithm') -> None:
        BaseThrottleAsyncBackend.initialize_algorithm(self, algorithm)
        script = algorithm.transaction_script(self.needs_transaction_script)
        # for mypy: we just checked this:
        assert script is not None  # noqa: S101
        object.__setattr__(  # noqa: PLC2801
            self,
            '_script',
            self.client.register_script(script),
        )

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
        script_result = cast(
            tuple[int, int, int],
            await self._script(
                keys=[cache_key],
                args=[throttle.max_requests, throttle.duration_in_seconds, 0],
            ),
        )
        cache_object = CachedRateLimit(
            history=[script_result[1]],
            time=script_result[2],
        )
        if script_result[0] == 0:
            raise TooManyRequestsError(
                headers=algorithm.report_usage(
                    endpoint,
                    controller,
                    throttle,
                    cache_object,
                ),
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
        script_result = cast(
            tuple[int, int, int],
            await self._script(
                keys=[cache_key],
                # read-only request with the last `1`:
                args=[throttle.max_requests, throttle.duration_in_seconds, 1],
            ),
        )
        return CachedRateLimit(
            history=[script_result[1]],
            time=script_result[2],
        )
