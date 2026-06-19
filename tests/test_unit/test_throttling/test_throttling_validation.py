from typing import Any

import pytest
from django.conf import LazySettings

from dmr import Controller, modify
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory
from dmr.throttling import (
    AsyncThrottle,
    Rate,
    SyncOrAsyncThrottle,
    SyncThrottle,
)


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


@pytest.mark.filterwarnings(
    'ignore::dmr.throttling.backends.django_cache.UnsafeCacheBackendWarning',
)
def test_sync_or_async_throttle_resolves_to_sync_via_settings(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures SyncOrAsyncThrottle resolves to SyncThrottle for sync."""
    settings.DMR_SETTINGS = {
        Settings.throttling: [
            SyncOrAsyncThrottle(
                SyncThrottle(1, Rate.second),
                AsyncThrottle(1, Rate.second),
            ),
        ],
    }

    class _SyncEndpointController(
        Controller[PydanticSerializer],
    ):
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SyncEndpointController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is not None
    assert isinstance(metadata.throttling_before_auth[0], SyncThrottle)


@pytest.mark.filterwarnings(
    'ignore::dmr.throttling.backends.django_cache.UnsafeCacheBackendWarning',
)
def test_sync_or_async_throttle_resolves_to_async_via_settings(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures SyncOrAsyncThrottle resolves to AsyncThrottle for async."""
    settings.DMR_SETTINGS = {
        Settings.throttling: [
            SyncOrAsyncThrottle(
                SyncThrottle(1, Rate.second),
                AsyncThrottle(1, Rate.second),
            ),
        ],
    }

    class _AsyncEndpointController(
        Controller[PydanticSerializer],
    ):
        async def get(self) -> str:
            raise NotImplementedError

    metadata = _AsyncEndpointController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is not None
    assert isinstance(metadata.throttling_before_auth[0], AsyncThrottle)


def test_sync_or_async_throttle_not_allowed_at_controller_level(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
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
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures SyncOrAsyncThrottle raises an error at endpoint level."""
    wrong_throttling: Any = [
        SyncOrAsyncThrottle(
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
def test_endpoint_metadata_never_has_sync_or_async_throttle_instance(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures resolved metadata contains no SyncOrAsyncThrottle instances."""
    instance = SyncOrAsyncThrottle(
        SyncThrottle(1, Rate.second),
        AsyncThrottle(1, Rate.second),
    )
    settings.DMR_SETTINGS = {
        Settings.throttling: [instance],
    }

    class _SyncEndpointController(
        Controller[PydanticSerializer],
    ):
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SyncEndpointController.api_endpoints['GET'].metadata
    assert metadata.throttling_before_auth is not None
    for throttle in metadata.throttling_before_auth:
        assert not isinstance(throttle, SyncOrAsyncThrottle)  # type: ignore[unreachable]


@pytest.mark.filterwarnings(
    'ignore::dmr.throttling.backends.django_cache.UnsafeCacheBackendWarning',
)
def test_same_instance_reused_for_sync_and_async(
    dmr_rf: DMRRequestFactory,
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
