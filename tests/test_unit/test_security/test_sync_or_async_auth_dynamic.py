import json
from http import HTTPStatus
from typing import Final, Self

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import SyncOrAsyncAuth
from dmr.security.http import HttpBasicAsyncAuth, HttpBasicSyncAuth, basic_auth
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


class _SyncAuth(HttpBasicSyncAuth):
    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        if username == 'test' and password == 'pass':  # noqa: S105
            return self
        return None


class _AsyncAuth(HttpBasicAsyncAuth):
    @override
    async def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        if username == 'test' and password == 'pass':  # noqa: S105
            return self
        return None


_AUTH: Final = SyncOrAsyncAuth(_SyncAuth(), _AsyncAuth())


def test_sync_or_async_auth_settings_sync(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures SyncOrAsyncAuth in settings resolves and enforces sync auth."""
    settings.DMR_SETTINGS = {Settings.auth: [_AUTH]}

    class _SyncController(Controller[PydanticSerializer]):
        def get(self) -> str:
            return 'authed'

    metadata = _SyncController.api_endpoints['GET'].metadata
    assert metadata.auth is not None
    assert isinstance(metadata.auth[0], _SyncAuth)

    # Valid credentials succeed:
    request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': basic_auth('test', 'pass')},
    )
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'

    # No credentials fail:
    request = dmr_rf.get('/whatever/')
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.asyncio
async def test_sync_or_async_auth_settings_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures SyncOrAsyncAuth in settings resolves and enforces async auth."""
    settings.DMR_SETTINGS = {Settings.auth: [_AUTH]}

    class _AsyncController(Controller[PydanticSerializer]):
        async def get(self) -> str:
            return 'authed'

    metadata = _AsyncController.api_endpoints['GET'].metadata
    assert metadata.auth is not None
    assert isinstance(metadata.auth[0], _AsyncAuth)

    # Valid credentials succeed:
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'Authorization': basic_auth('test', 'pass')},
    )
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'

    # No credentials fail:
    request = dmr_async_rf.get('/whatever/')
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
