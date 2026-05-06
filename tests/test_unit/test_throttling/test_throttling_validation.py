import pytest

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle


def test_throttle_sync_mix(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures sync validation works."""
    with pytest.raises(EndpointMetadataError, match='SyncThrottle'):

        class _SyncEndpointController(
            Controller[PydanticSerializer],
        ):
            throttling = (AsyncThrottle(1, Rate.second),)

            def get(self) -> str:
                raise NotImplementedError


def test_throttle_async_mix(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures async validation works."""
    with pytest.raises(EndpointMetadataError, match='AsyncThrottle'):

        class _AsyncEndpointController(
            Controller[PydanticSerializer],
        ):
            throttling = (SyncThrottle(1, Rate.second),)

            async def get(self) -> str:
                raise NotImplementedError
