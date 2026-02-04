import json
from http import HTTPStatus
from typing import Any, final

import pytest
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from django_modern_rest import Controller, modify
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.openapi.objects.security_requirement import (
    SecurityRequirement,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security import AsyncAuth, SyncAuth
from django_modern_rest.security.http import (
    HttpBasicAsyncAuth,
    HttpBasicSyncAuth,
)
from django_modern_rest.serializer import BaseSerializer
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


class _HttpBasicSync(HttpBasicSyncAuth):
    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Any | None:
        raise NotImplementedError  # will not reach this ever


class _HttpBasicAsync(HttpBasicAsyncAuth):
    @override
    async def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Any | None:
        raise NotImplementedError  # will not reach this ever


class _PermissionDeniedSync(SyncAuth):
    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Any | None:
        raise PermissionDenied

    @property
    @override
    def security_scheme(self) -> Components:
        raise NotImplementedError

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        raise NotImplementedError


class _PermissionDeniedAsync(AsyncAuth):
    @override
    async def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Any | None:
        raise PermissionDenied

    @property
    @override
    def security_scheme(self) -> Components:
        raise NotImplementedError

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        raise NotImplementedError


@final
class _SyncController(Controller[PydanticSerializer]):
    @modify(auth=[_PermissionDeniedSync(), _HttpBasicSync()])
    def get(self) -> str:
        raise NotImplementedError


def test_sync_permission_denied(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that sync controllers work with PermissionDenied."""
    request = dmr_rf.get('/whatever/')

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@final
class _AsyncController(Controller[PydanticSerializer]):
    @modify(auth=[_PermissionDeniedAsync(), _HttpBasicAsync()])
    async def get(self) -> str:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_async_permission_denied(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that sync controllers work with PermissionDenied."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
