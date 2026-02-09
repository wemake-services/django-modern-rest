import pytest

from django_modern_rest import Controller, modify
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)


def test_sync_endpoint_requires_sync_auth() -> None:
    """Ensures that sync endpoints require sync auth."""
    with pytest.raises(EndpointMetadataError, match=r'base\.SyncAuth'):

        class _SyncController(Controller[PydanticSerializer]):
            @modify(auth=[DjangoSessionAsyncAuth()])
            def get(self) -> str:
                raise NotImplementedError


def test_async_endpoint_requires_async_auth() -> None:
    """Ensures that async endpoints require async auth."""
    with pytest.raises(EndpointMetadataError, match=r'base\.AsyncAuth'):

        class _AsyncController(Controller[PydanticSerializer]):
            @modify(auth=[DjangoSessionSyncAuth()])
            async def get(self) -> str:
                raise NotImplementedError


def test_sync_controller_requires_sync_auth() -> None:
    """Ensures that sync controllers require sync auth."""
    with pytest.raises(EndpointMetadataError, match=r'base\.SyncAuth'):

        class _SyncController(Controller[PydanticSerializer]):
            auth = [DjangoSessionAsyncAuth()]

            def get(self) -> str:
                raise NotImplementedError


def test_async_controller_requires_async_auth() -> None:
    """Ensures that async controllers require async auth."""
    with pytest.raises(EndpointMetadataError, match=r'base\.AsyncAuth'):

        class _AsyncController(Controller[PydanticSerializer]):
            auth = [DjangoSessionSyncAuth()]

            async def get(self) -> str:
                raise NotImplementedError
