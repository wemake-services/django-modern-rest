from typing import Any, Final, Self

import pytest
from django.conf import LazySettings
from typing_extensions import override

from dmr import Controller, modify
from dmr.endpoint import Endpoint
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import SyncOrAsyncAuth
from dmr.security.http import HttpBasicAsyncAuth, HttpBasicSyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory


class _SyncAuth(HttpBasicSyncAuth):
    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        return self


class _AsyncAuth(HttpBasicAsyncAuth):
    @override
    async def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        return self


_AUTH: Final = SyncOrAsyncAuth(_SyncAuth(), _AsyncAuth())


def test_sync_or_async_auth_resolves_to_sync_via_settings(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures SyncOrAsyncAuth resolves to SyncAuth for sync endpoints."""
    settings.DMR_SETTINGS = {Settings.auth: [_AUTH]}

    class _SyncController(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SyncController.api_endpoints['GET'].metadata
    assert metadata.auth is not None
    assert isinstance(metadata.auth[0], HttpBasicSyncAuth)


def test_sync_or_async_auth_resolves_to_async_via_settings(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures SyncOrAsyncAuth resolves to AsyncAuth for async endpoints."""
    settings.DMR_SETTINGS = {Settings.auth: [_AUTH]}

    class _AsyncController(Controller[PydanticSerializer]):
        async def get(self) -> str:
            raise NotImplementedError

    metadata = _AsyncController.api_endpoints['GET'].metadata
    assert metadata.auth is not None
    assert isinstance(metadata.auth[0], HttpBasicAsyncAuth)


def test_sync_or_async_auth_not_allowed_at_controller_level(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures SyncOrAsyncAuth raises an error at controller level."""
    with pytest.raises(EndpointMetadataError, match='SyncOrAsyncAuth'):

        class _SyncController(Controller[PydanticSerializer]):
            auth = (_AUTH,)  # type: ignore[assignment]

            def get(self) -> str:
                raise NotImplementedError


def test_sync_or_async_auth_not_allowed_at_endpoint_level(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures SyncOrAsyncAuth raises an error at endpoint level."""
    wrong_auth: Any = [_AUTH]
    with pytest.raises(EndpointMetadataError, match='SyncOrAsyncAuth'):

        class _SyncController(Controller[PydanticSerializer]):
            @modify(auth=wrong_auth)
            def get(self) -> str:
                raise NotImplementedError


def test_endpoint_metadata_never_has_sync_or_async_auth_instance(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures resolved metadata contains no SyncOrAsyncAuth instances."""
    settings.DMR_SETTINGS = {Settings.auth: [_AUTH]}

    class _SyncController(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    metadata = _SyncController.api_endpoints['GET'].metadata
    assert metadata.auth is not None
    for auth in metadata.auth:
        assert not isinstance(auth, SyncOrAsyncAuth)  # type: ignore[unreachable]


def test_same_instance_reused_for_sync_and_async(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures the same SyncOrAsyncAuth yields the same inner instances."""
    sync_auth = _SyncAuth()
    async_auth = _AsyncAuth()
    instance = SyncOrAsyncAuth(sync_auth, async_auth)
    settings.DMR_SETTINGS = {Settings.auth: [instance]}

    class _SyncController(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    class _AsyncController(Controller[PydanticSerializer]):
        async def get(self) -> str:
            raise NotImplementedError

    sync_meta = _SyncController.api_endpoints['GET'].metadata
    async_meta = _AsyncController.api_endpoints['GET'].metadata

    assert sync_meta.auth is not None
    assert async_meta.auth is not None
    assert sync_meta.auth[0] is sync_auth
    assert async_meta.auth[0] is async_auth


def test_sync_auth_in_settings_raises_for_async_endpoint(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures sync auth in settings raises for async endpoints."""
    settings.DMR_SETTINGS = {Settings.auth: [_SyncAuth()]}

    with pytest.raises(EndpointMetadataError, match='AsyncAuth'):

        class _AsyncController(Controller[PydanticSerializer]):
            async def get(self) -> str:
                raise NotImplementedError


def test_async_auth_in_settings_raises_for_sync_endpoint(  # noqa: WPS118
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures async auth in settings raises for sync endpoints."""
    settings.DMR_SETTINGS = {Settings.auth: [_AsyncAuth()]}

    with pytest.raises(EndpointMetadataError, match='SyncAuth'):

        class _SyncController(Controller[PydanticSerializer]):
            def get(self) -> str:
                raise NotImplementedError
