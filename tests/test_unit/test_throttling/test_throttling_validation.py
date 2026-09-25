import pytest
from django.conf import LazySettings

from dmr import Controller, modify
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import Settings
from dmr.throttling import (
    AsyncThrottle,
    Rate,
    SyncOrAsyncThrottle,
    SyncThrottle,
)


def test_throttle_sync_mix() -> None:
    """Ensures sync validation works."""
    with pytest.raises(EndpointMetadataError, match='SyncThrottle'):

        class _SyncEndpointController(
            Controller[PydanticSerializer],
        ):
            throttling = (AsyncThrottle(1, Rate.second),)

            def get(self) -> str:
                raise NotImplementedError


def test_throttle_async_mix() -> None:
    """Ensures async validation works."""
    with pytest.raises(EndpointMetadataError, match='AsyncThrottle'):

        class _AsyncEndpointController(
            Controller[PydanticSerializer],
        ):
            throttling = (SyncThrottle(1, Rate.second),)

            async def get(self) -> str:
                raise NotImplementedError


def test_sync_or_async_throttle_not_allowed_at_controller_level(  # noqa: WPS118
) -> None:
    """Ensures SyncOrAsyncThrottle raises an error at controller level."""
    with pytest.raises(EndpointMetadataError, match='SyncOrAsyncThrottle'):

        class _SyncEndpointController(
            Controller[PydanticSerializer],
        ):
            throttling = (  # type: ignore[assignment]
                SyncOrAsyncThrottle(
                    SyncThrottle(1, Rate.second),
                    AsyncThrottle(1, Rate.second),
                ),
            )

            def get(self) -> str:
                raise NotImplementedError


def test_sync_or_async_throttle_not_allowed_at_endpoint_level(  # noqa: WPS118
) -> None:
    """Ensures SyncOrAsyncThrottle raises an error at endpoint level."""
    wrong_throttling: list[SyncThrottle] = [  # pyrefly: ignore[bad-assignment]
        SyncOrAsyncThrottle(  # type: ignore[list-item]
            SyncThrottle(1, Rate.second),
            AsyncThrottle(1, Rate.second),
        ),
    ]
    with pytest.raises(EndpointMetadataError, match='SyncOrAsyncThrottle'):

        class _SyncEndpointController(
            Controller[PydanticSerializer],
        ):
            @modify(throttling=wrong_throttling)
            def get(self) -> str:
                raise NotImplementedError


@pytest.mark.filterwarnings(
    'ignore::dmr.throttling.backends.django_cache.UnsafeCacheBackendWarning',
)
def test_same_instance_reused_for_sync_and_async(
    settings: LazySettings,
) -> None:
    """Ensures the same SyncOrAsyncThrottle yields the same inner instances."""
    sync_throttle = SyncThrottle(1, Rate.second)
    async_throttle = AsyncThrottle(1, Rate.second)
    instance = SyncOrAsyncThrottle(sync_throttle, async_throttle)
    settings.DMR_SETTINGS = {
        Settings.throttling: [instance],
    }

    class _SyncController(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    class _AsyncController(Controller[PydanticSerializer]):
        async def get(self) -> str:
            raise NotImplementedError

    sync_meta = _SyncController.api_endpoints['GET'].metadata
    async_meta = _AsyncController.api_endpoints['GET'].metadata

    assert sync_meta.throttling_before_auth is not None
    assert async_meta.throttling_before_auth is not None
    assert sync_meta.throttling_before_auth[0] is sync_throttle
    assert async_meta.throttling_before_auth[0] is async_throttle
