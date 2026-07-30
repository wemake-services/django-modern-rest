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
from dmr.security.token.token import DEFAULT_TOKEN_ALGORITHM, DEFAULT_TOKEN_SALT
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('auth_salt', 'auth_algorithm', 'expected_status'),
    [
        ('custom_salt', 'sha512', HTTPStatus.OK),
        (DEFAULT_TOKEN_SALT, DEFAULT_TOKEN_ALGORITHM, HTTPStatus.UNAUTHORIZED),
    ],
)
def test_sync_token_auth_custom_salt_and_algorithm(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    *,
    auth_salt: str,
    auth_algorithm: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures auth with matching custom salt/algorithm succeeds; mismatched params fail."""

    class _CustomParamsController(Controller[PydanticFastSerializer]):
        auth = (
            HeaderTokenSyncAuth(token_salt=auth_salt, token_algorithm=auth_algorithm),
        )

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='custom-params',
        token_salt='custom_salt',
        token_algorithm='sha512',
    )
    request = dmr_rf.get('/whatever/', headers={'X-API-Token': raw_token})

    response = _CustomParamsController.as_view()(request)

    assert response.status_code == expected_status


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('auth_secret', 'expected_status'),
    [
        ('custom-secret', HTTPStatus.OK),
        (None, HTTPStatus.UNAUTHORIZED),
    ],
)
def test_sync_token_auth_custom_secret(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    *,
    auth_secret: str | None,
    expected_status: HTTPStatus,
) -> None:
    """Ensures auth with matching custom secret succeeds; wrong secret fails."""

    class _CustomSecretController(Controller[PydanticFastSerializer]):
        auth = (HeaderTokenSyncAuth(token_secret=auth_secret),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='custom-secret',
        token_secret='custom-secret',
    )
    request = dmr_rf.get('/whatever/', headers={'X-API-Token': raw_token})

    response = _CustomSecretController.as_view()(request)

    assert response.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('auth_salt', 'auth_algorithm', 'expected_status'),
    [
        ('custom_salt', 'sha512', HTTPStatus.OK),
        (DEFAULT_TOKEN_SALT, DEFAULT_TOKEN_ALGORITHM, HTTPStatus.UNAUTHORIZED),
    ],
)
async def test_async_token_auth_custom_salt_and_algorithm(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    *,
    auth_salt: str,
    auth_algorithm: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures async auth with matching custom salt/algorithm succeeds; mismatched params fail."""

    class _CustomParamsController(Controller[PydanticFastSerializer]):
        auth = (
            HeaderTokenAsyncAuth(token_salt=auth_salt, token_algorithm=auth_algorithm),
        )

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-custom-params',
        token_salt='custom_salt',
        token_algorithm='sha512',
    )
    request = dmr_async_rf.get('/whatever/', headers={'X-API-Token': raw_token})

    response = await dmr_async_rf.wrap(_CustomParamsController.as_view()(request))

    assert response.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('auth_secret', 'expected_status'),
    [
        ('custom-secret', HTTPStatus.OK),
        (None, HTTPStatus.UNAUTHORIZED),
    ],
)
async def test_async_token_auth_custom_secret(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    *,
    auth_secret: str | None,
    expected_status: HTTPStatus,
) -> None:
    """Ensures async auth with matching custom secret succeeds; wrong secret fails."""

    class _CustomSecretController(Controller[PydanticFastSerializer]):
        auth = (HeaderTokenAsyncAuth(token_secret=auth_secret),)

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-custom-secret',
        token_secret='custom-secret',
    )
    request = dmr_async_rf.get('/whatever/', headers={'X-API-Token': raw_token})

    response = await dmr_async_rf.wrap(_CustomSecretController.as_view()(request))

    assert response.status_code == expected_status
