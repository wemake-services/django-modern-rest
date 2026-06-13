import pytest

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory
from dmr.throttling import AsyncThrottle, DynamicThrottle, Rate, SyncThrottle


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


def test_dynamic_throttle_no_error_on_sync(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures DynamicThrottle does not raise EndpointMetadataError for sync."""

    class _SyncEndpointController(
        Controller[PydanticSerializer],
    ):
        throttling = (DynamicThrottle(1, Rate.second),)

        def get(self) -> str:
            raise NotImplementedError

    metadata = _SyncEndpointController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is not None
    assert isinstance(metadata.throttling_before_auth[0], SyncThrottle)


def test_dynamic_throttle_no_error_on_async(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures DynamicThrottle does not raise EndpointMetadataError."""

    class _AsyncEndpointController(
        Controller[PydanticSerializer],
    ):
        throttling = (DynamicThrottle(1, Rate.second),)

        async def get(self) -> str:
            raise NotImplementedError

    metadata = _AsyncEndpointController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is not None
    assert isinstance(metadata.throttling_before_auth[0], AsyncThrottle)
