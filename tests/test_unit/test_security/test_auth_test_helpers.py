import json
from http import HTTPStatus
from typing import Final, final

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.http import HttpResponse

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import request_auth
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory, disabled_auth

sync_auth: Final = DjangoSessionSyncAuth()


@final
class _SyncController(Controller[PydanticSerializer]):
    @modify(auth=[sync_auth])
    def get(self) -> str:
        return 'authed'


def test_disabled_auth_sync(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that sync controllers work with django session auth."""
    user = User()
    request = dmr_rf.get('/whatever/')

    with disabled_auth(_SyncController, request=request, user=user):
        assert request.user == user
        assert async_to_sync(request.auser)() == user
        assert request_auth(request) is None
        response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'authed'


async_auth: Final = DjangoSessionAsyncAuth()


@final
class _AsyncController(Controller[PydanticSerializer]):
    auth = [async_auth]

    async def get(self) -> str:
        return 'authed'


@pytest.mark.asyncio
async def test_async_disabled_auth(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that async controllers work with disabling auth."""
    user = User()
    request = dmr_async_rf.get('/whatever/')

    with disabled_auth(
        _AsyncController,
        request=request,
        user=user,
        auth=async_auth,
    ):
        assert request.user == user
        assert await request.auser() == user
        assert request_auth(request) == async_auth
        assert request_auth(request, strict=True) == async_auth
        response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'authed'


def test_disabled_auth_missing_method(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that you can't disable a missing method's auth."""
    user = User()
    request = dmr_rf.post('/whatever/')

    with pytest.raises(ValueError, match='has no endpoint'):
        disabled_auth(  # noqa: PLC2801
            _SyncController,
            request=request,
            user=user,
        ).__enter__()


@final
class _RegularController(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


def test_disabled_auth_missing_auth(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that you can't disable method's missing auth."""
    user = User()
    request = dmr_rf.get('/whatever/')

    with pytest.raises(ValueError, match='has no auth'):
        disabled_auth(  # noqa: PLC2801
            _RegularController,
            request=request,
            user=user,
        ).__enter__()


def test_disabled_auth_mixed_async(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that you can't mix async and sync logic."""
    user = User()
    request = dmr_rf.get('/whatever/')

    with pytest.raises(ValueError, match='Using async auth'):
        disabled_auth(  # noqa: PLC2801
            _SyncController,
            request=request,
            user=user,
            auth=async_auth,
        ).__enter__()
    with pytest.raises(ValueError, match='Using sync auth'):
        disabled_auth(  # noqa: PLC2801
            _AsyncController,
            request=request,
            user=user,
            auth=sync_auth,
        ).__enter__()
