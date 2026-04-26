from typing import Any

import pytest

try:
    import redis
except ImportError:  # pragma: no cover
    pytest.skip(reason='redis is not installed', allow_module_level=True)

from redis import asyncio as aioredis
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.algorithms import BaseThrottleAlgorithm
from dmr.throttling.backends import CachedRateLimit
from dmr.throttling.backends.redis import AsyncRedis, SyncRedis


class _NoLuaAlgo(BaseThrottleAlgorithm):
    @override
    def access(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        throttle: SyncThrottle | AsyncThrottle,
        cache_object: CachedRateLimit | None,
    ) -> CachedRateLimit:
        raise NotImplementedError

    @override
    def report_usage(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        throttle: SyncThrottle | AsyncThrottle,
        cache_object: CachedRateLimit | None,
    ) -> dict[str, str]:
        raise NotImplementedError


def test_redis_with_unsupported_algorithm(
    dmr_rf: DMRRequestFactory,
    redis_client: 'redis.Redis[Any]',
) -> None:
    """Ensures that throttle information can be served on success."""
    with pytest.raises(EndpointMetadataError, match='Cannot use backend'):

        class _Controller(Controller[PydanticSerializer]):
            throttling = [
                SyncThrottle(
                    1,
                    Rate.minute,
                    backend=SyncRedis(redis_client),
                    algorithm=_NoLuaAlgo(),
                ),
            ]


def test_async_redis_with_unsupported_algorithm(
    dmr_rf: DMRRequestFactory,
    redis_async_client: 'aioredis.Redis[Any]',
) -> None:
    """Ensures that throttle information can be served on success."""
    with pytest.raises(EndpointMetadataError, match='Cannot use backend'):

        class _Controller(Controller[PydanticSerializer]):
            throttling = [
                AsyncThrottle(
                    1,
                    Rate.minute,
                    backend=AsyncRedis(redis_async_client),
                    algorithm=_NoLuaAlgo(),
                ),
            ]
