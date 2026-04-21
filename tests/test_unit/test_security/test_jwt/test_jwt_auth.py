import datetime as dt
import json
from http import HTTPStatus

import pydantic
import pytest
from asgiref.sync import async_to_sync
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpResponse

from dmr import Controller, Query
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import request_auth
from dmr.security.jwt import JWTAsyncAuth, JWToken, JWTSyncAuth, request_jwt
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


class _QueryModel(pydantic.BaseModel):
    user_id: int


class _AsyncController(Controller[PydanticFastSerializer]):
    auth = (JWTAsyncAuth(),)

    async def get(self, parsed_query: Query[_QueryModel]) -> str:
        auser = await self.request.auser()
        assert auser.is_authenticated
        assert auser.pk == parsed_query.user_id

        assert self.request.user.is_authenticated
        assert self.request.user.pk == parsed_query.user_id

        assert request_jwt(self.request)

        return 'authed'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_jwt_view(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures that async controllers work with django session auth."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=str(admin_user.pk),
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_async_rf.get(
        f'/whatever/?user_id={admin_user.pk}',
        headers={'Authorization': f'Bearer {token}'},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert isinstance(request_auth(request), JWTAsyncAuth)
    assert isinstance(
        request_auth(request, strict=True),
        JWTAsyncAuth,
    )
    assert json.loads(response.content) == 'authed'


class _SyncController(Controller[PydanticFastSerializer]):
    auth = (JWTSyncAuth(),)

    def get(self, parsed_query: Query[_QueryModel]) -> str:
        assert self.request.user.is_authenticated
        assert self.request.user.is_active
        assert self.request.user.pk == parsed_query.user_id

        auser = async_to_sync(self.request.auser)()
        assert auser.is_authenticated
        assert auser.is_active
        assert auser.pk == parsed_query.user_id

        assert request_jwt(self.request)

        return 'authed'


@pytest.mark.django_db
def test_sync_jwt_view(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures that sync controllers work with django session auth."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=str(admin_user.pk),
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        f'/whatever/?user_id={admin_user.pk}',
        headers={'Authorization': f'Bearer {token}'},
    )

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert isinstance(request_auth(request), JWTSyncAuth)
    assert isinstance(request_auth(request, strict=True), JWTSyncAuth)
    assert json.loads(response.content) == 'authed'
