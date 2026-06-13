import pytest
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import AsyncThrottle, SyncThrottle
from dmr.throttling.algorithms import (
    BaseThrottleAlgorithm,
    LeakyBucket,
    SimpleRate,
)
from dmr.throttling.backends import (
    BaseThrottleAsyncBackend,
    BaseThrottleSyncBackend,
    CachedRateLimit,
)


class _NeedsSqlSync(BaseThrottleSyncBackend):
    needs_transaction_script = 'sql'

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
        raise NotImplementedError

    @override
    def get(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        throttle: SyncThrottle,
        *,
        cache_key: str,
    ) -> CachedRateLimit | None:
        raise NotImplementedError


@pytest.mark.parametrize(
    'algorithm',
    [
        LeakyBucket(),
        SimpleRate(),
    ],
)
def test_unsupported_sync_backend(
    dmr_rf: DMRRequestFactory,
    *,
    algorithm: BaseThrottleAlgorithm,
) -> None:
    """Ensure that unsupported algorithms raise."""
    with pytest.raises(EndpointMetadataError, match='Cannot use backend'):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                SyncThrottle(
                    1,
                    5,
                    algorithm=algorithm,
                    backend=_NeedsSqlSync(),
                ),
            ]


class _NeedsSqlAsync(BaseThrottleAsyncBackend):
    needs_transaction_script = 'sql'

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
        raise NotImplementedError

    @override
    async def get(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        throttle: AsyncThrottle,
        *,
        cache_key: str,
    ) -> CachedRateLimit | None:
        raise NotImplementedError


@pytest.mark.parametrize(
    'algorithm',
    [
        LeakyBucket(),
        SimpleRate(),
    ],
)
def test_unsupported_async_backend(
    dmr_rf: DMRRequestFactory,
    *,
    algorithm: BaseThrottleAlgorithm,
) -> None:
    """Ensure that unsupported algorithms raise."""
    with pytest.raises(EndpointMetadataError, match='Cannot use backend'):

        class _Controller(Controller[PydanticFastSerializer]):
            throttling = [
                AsyncThrottle(
                    1,
                    5,
                    algorithm=algorithm,
                    backend=_NeedsSqlAsync(),
                ),
            ]
