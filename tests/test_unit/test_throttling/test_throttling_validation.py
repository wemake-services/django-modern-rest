import pytest

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.backends.django_cache import UnsafeCacheBackendWarning


def test_throttle_sync_mix() -> None:
    """Ensures sync validation works."""
    with pytest.warns(UnsafeCacheBackendWarning):
        bad_throttle = AsyncThrottle(1, Rate.second)

    with pytest.raises(EndpointMetadataError, match='SyncThrottle'):

        class _SyncEndpointController(Controller[PydanticSerializer]):
            throttling = (bad_throttle,)

            def get(self) -> str:
                return 'inside'  # pragma: no cover


def test_throttle_async_mix() -> None:
    """Ensures async validation works."""
    with pytest.warns(UnsafeCacheBackendWarning):
        bad_throttle = SyncThrottle(1, Rate.second)

    with pytest.raises(EndpointMetadataError, match='AsyncThrottle'):

        class _AsyncEndpointController(Controller[PydanticSerializer]):
            throttling = (bad_throttle,)

            async def get(self) -> str:
                return 'inside'  # pragma: no cover
