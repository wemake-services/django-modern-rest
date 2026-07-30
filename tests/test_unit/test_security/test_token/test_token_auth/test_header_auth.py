import datetime as dt
import json
from http import HTTPStatus
from typing import Final, final

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.exceptions import NotAuthenticatedError
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import request_auth
from dmr.security.token import (
    HeaderTokenAsyncAuth,
    HeaderTokenSyncAuth,
    request_token,
)
from dmr.security.token.app.models import Token
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_CORRECT_TEMPLATE: Final = '{0}'


@final
class _SyncController(Controller[PydanticFastSerializer]):
    auth = (HeaderTokenSyncAuth(),)

    def get(self) -> str:
        assert self.request.user.is_authenticated
        assert self.request.user.is_active
        auser = async_to_sync(self.request.auser)()
        assert auser.is_authenticated
        assert auser.is_active
        assert request_token(self.request)
        return 'authed'


@pytest.mark.django_db
def test_sync_token_auth_success(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures sync controllers work with token auth."""
    token, raw_token = Token.issue(
        user=admin_user,
        name='test',
    )
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = _SyncController.as_view()(request)

    token.refresh_from_db()
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert isinstance(request_auth(request), HeaderTokenSyncAuth)
    assert isinstance(request_auth(request, strict=True), HeaderTokenSyncAuth)
    assert request_token(request) == token
    assert token.last_used_at is None
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
def test_sync_token_auth_missing_header(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures a missing header falls through to 401."""
    request = dmr_rf.get('/whatever/')

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert request_auth(request) is None
    with pytest.raises(AttributeError, match='__dmr_auth__'):
        request_auth(request, strict=True)
    assert request_token(request) is None
    with pytest.raises(AttributeError, match='__dmr_token__'):
        request_token(request, strict=True)
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
def test_sync_token_auth_unknown_token(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures an unknown raw token returns 401."""
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': 'not-a-real-token'},
    )

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('header_name', 'header_value', 'expected_status'),
    [
        ('X-API-Token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('X-API-Token', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('X-API-Token', 'Token {0}', HTTPStatus.UNAUTHORIZED),
        ('X-API-Token', 'Bearer {0}', HTTPStatus.UNAUTHORIZED),
        ('Authorization', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('Authorization', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('Authorization', 'Bearer {0}', HTTPStatus.UNAUTHORIZED),
        ('Authorization', 'Token {0}', HTTPStatus.OK),
    ],
)
def test_sync_token_auth_prefix_stripping(
    dmr_rf: DMRAsyncRequestFactory,
    admin_user: User,
    *,
    header_name: str,
    header_value: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures a custom prefix is required for `Authorization` auth."""

    class _PrefixController(Controller[PydanticFastSerializer]):
        auth = (
            HeaderTokenSyncAuth(header_name='Authorization', prefix='Token'),
        )

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='prefix-test',
        expires_at=None,
    )

    request = dmr_rf.get(
        '/whatever/',
        headers={header_name: header_value.format(raw_token)},
    )
    response = _PrefixController.as_view()(request)

    assert response.status_code == expected_status


@pytest.mark.django_db
def test_sync_token_auth_revoked(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures a revoked token returns 401."""
    token, raw_token = Token.issue(
        user=admin_user,
        name='to-revoke',
    )
    token.revoke()

    request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_sync_token_auth_expired(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures an expired token returns 401."""
    _, raw_token = Token.issue(
        user=admin_user,
        name='expired',
        expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1),
    )
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_sync_token_auth_inactive_user(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures an active token for an inactive user returns 401."""
    admin_user.is_active = False
    admin_user.save(update_fields=['is_active'])

    _, raw_token = Token.issue(
        user=admin_user,
        name='inactive-user',
    )
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@final
class _AsyncController(Controller[PydanticFastSerializer]):
    auth = (HeaderTokenAsyncAuth(),)

    async def get(self) -> str:
        auser = await self.request.auser()
        assert auser.is_authenticated
        assert auser.is_active
        assert self.request.user.is_authenticated
        assert self.request.user.is_active
        assert request_token(self.request)
        return 'authed'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_token_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures async controllers work with token auth."""
    token, raw_token = await Token.aissue(
        user=admin_user,
        name='async-test',
    )
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    await token.arefresh_from_db()
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert isinstance(request_auth(request), HeaderTokenAsyncAuth)
    assert isinstance(request_auth(request, strict=True), HeaderTokenAsyncAuth)
    assert request_token(request) == token
    assert token.last_used_at is None
    assert json.loads(response.content) == 'authed'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_token_auth_missing_header(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures a missing header falls through to 401."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert request_auth(request) is None
    with pytest.raises(AttributeError, match='__dmr_auth__'):
        request_auth(request, strict=True)
    assert request_token(request) is None
    with pytest.raises(AttributeError, match='__dmr_token__'):
        request_token(request, strict=True)
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_token_auth_revoked(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures a revoked token returns 401 in async flow."""
    token, raw_token = await Token.aissue(
        user=admin_user,
        name='async-revoked',
    )
    await token.arevoke()

    request = dmr_async_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_token_auth_unknown_token(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures an unknown raw token returns 401 in async flow."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'X-API-Token': 'not-a-real-token'},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_token_auth_expired(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures an expired token returns 401 in async flow."""
    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-expired',
        expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1),
    )
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_token_auth_inactive_user(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures an active token for an inactive user returns 401 (async)."""
    admin_user.is_active = False
    await admin_user.asave(update_fields=['is_active'])

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-inactive-user',
    )
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('header_name', 'header_value', 'expected_status'),
    [
        ('X-API-Token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('X-API-Token', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('X-API-Token', 'Token {0}', HTTPStatus.UNAUTHORIZED),
        ('X-API-Token', 'Bearer {0}', HTTPStatus.UNAUTHORIZED),
        ('Authorization', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('Authorization', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('Authorization', 'Bearer {0}', HTTPStatus.UNAUTHORIZED),
        ('Authorization', 'Token {0}', HTTPStatus.OK),
    ],
)
async def test_async_token_auth_prefix_stripping(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    *,
    header_name: str,
    header_value: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures a custom prefix is required for `Authorization` auth."""

    class _PrefixController(Controller[PydanticFastSerializer]):
        auth = (
            HeaderTokenAsyncAuth(header_name='Authorization', prefix='Token'),
        )

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='prefix-test',
        expires_at=None,
    )

    request = dmr_async_rf.get(
        '/whatever/',
        headers={header_name: header_value.format(raw_token)},
    )
    response = await dmr_async_rf.wrap(_PrefixController.as_view()(request))
    assert response.status_code == expected_status


@pytest.mark.django_db
def test_sync_token_auth_no_last_used_update(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures update_last_used=True sets the last_used_at write (sync)."""

    @final
    class _NoUpdateController(Controller[PydanticFastSerializer]):
        auth = (HeaderTokenSyncAuth(update_last_used=True),)

        def get(self) -> str:
            return 'authed'

    token, raw_token = Token.issue(
        user=admin_user,
        name='no-update-test',
    )
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = _NoUpdateController.as_view()(request)

    token.refresh_from_db()
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(token.last_used_at, dt.datetime)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_token_auth_no_last_used_update(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures update_last_used=True sets last_used_at write (async)."""

    @final
    class _NoUpdateAsyncController(Controller[PydanticFastSerializer]):
        auth = (HeaderTokenAsyncAuth(update_last_used=True),)

        async def get(self) -> str:
            return 'authed'

    token, raw_token = await Token.aissue(
        user=admin_user,
        name='async-no-update-test',
    )
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = await dmr_async_rf.wrap(
        _NoUpdateAsyncController.as_view()(request),
    )

    await token.arefresh_from_db()
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(token.last_used_at, dt.datetime)


def test_token_model_returns_token_class() -> None:
    """token_model() returns the Token model for both sync and async auth."""
    assert HeaderTokenSyncAuth().token_model is Token
    assert HeaderTokenAsyncAuth().token_model is Token


def test_sync_check_token_passes_for_active_token() -> None:
    """check_token() does not raise when the token is active."""
    token = Token(expires_at=None, revoked_at=None)
    HeaderTokenSyncAuth().check_token(token)


def test_sync_check_token_raises_inactive() -> None:
    """check_token() raises NotAuthenticatedError when the token is inactive."""
    token = Token(revoked_at=dt.datetime.now(dt.UTC))
    with pytest.raises(NotAuthenticatedError):
        HeaderTokenSyncAuth().check_token(token)


@pytest.mark.asyncio
async def test_async_check_token_passes_active() -> None:
    """Async check_token() does not raise when the token is active."""
    token = Token(expires_at=None, revoked_at=None)
    await HeaderTokenAsyncAuth().check_token(token)


@pytest.mark.asyncio
async def test_async_check_token_raises_inactive() -> None:
    """Async check_token() raises NotAuthenticatedError for inactive tokens."""
    token = Token(revoked_at=dt.datetime.now(dt.UTC))
    with pytest.raises(NotAuthenticatedError):
        await HeaderTokenAsyncAuth().check_token(token)
