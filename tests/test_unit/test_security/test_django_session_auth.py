import json
from http import HTTPStatus
from typing import final

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from inline_snapshot import snapshot

from django_modern_rest import Controller, modify
from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _SyncController(Controller[PydanticSerializer]):
    @modify(auth=[DjangoSessionSyncAuth()])
    def get(self) -> str:
        return 'authed'


def test_sync_session_auth_success(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that sync controllers work with django session auth."""
    request = dmr_rf.get('/whatever/')
    request.user = User()

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


def test_sync_session_auth_failure(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that sync controllers work with django session auth."""
    request = dmr_rf.get('/whatever/')
    request.user = AnonymousUser()

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'value_error',
                'loc': [],
                'msg': 'Value error, Not authenticated',
                'input': '',
                'ctx': {'error': 'Not authenticated'},
            },
        ],
    })


@final
class _AsyncController(Controller[PydanticSerializer]):
    auth = [DjangoSessionAsyncAuth()]

    async def get(self) -> str:
        return 'authed'


@pytest.mark.asyncio
async def test_async_session_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that async controllers work with django session auth."""
    request = dmr_async_rf.get('/whatever/')
    request.user = User()

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.asyncio
async def test_async_session_auth_failure(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that async controllers work with django session auth."""
    request = dmr_async_rf.get('/whatever/')
    request.user = AnonymousUser()

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'value_error',
                'loc': [],
                'msg': 'Value error, Not authenticated',
                'input': '',
                'ctx': {'error': 'Not authenticated'},
            },
        ],
    })


@pytest.mark.parametrize('typ', [DjangoSessionSyncAuth, DjangoSessionAsyncAuth])
def test_schema(
    typ: type[DjangoSessionSyncAuth | DjangoSessionAsyncAuth],
) -> None:
    """Ensures that security scheme is correct for django session auth."""
    instance = typ()
    scheme = instance.security_scheme

    assert isinstance(scheme, Components)
    assert scheme.security_schemes
    assert len(scheme.security_schemes) == 1
    assert instance.security_requirement == snapshot({'django_session': []})
