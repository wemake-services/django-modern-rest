import datetime as dt
import json
from http import HTTPStatus
from typing import final

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import request_auth
from dmr.security.token import (
    CookieTokenAsyncAuth,
    CookieTokenSyncAuth,
    QueryTokenAsyncAuth,
    QueryTokenSyncAuth,
    TokenAsyncAuth,
    TokenSyncAuth,
    request_token,
)
from dmr.security.token.models import Token
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _SyncController(Controller[PydanticFastSerializer]):
    auth = (TokenSyncAuth(),)

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
    token, raw_token = Token.objects.create_token(
        user=admin_user,
        name='test',
    )
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert isinstance(request_auth(request), TokenSyncAuth)
    assert isinstance(request_auth(request, strict=True), TokenSyncAuth)
    assert request_token(request) == token
    token.refresh_from_db()
    assert token.last_used_at is not None
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
def test_sync_token_auth_custom_header_e2e(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures custom header auth works end-to-end."""

    @final
    class _CustomHeaderController(Controller[PydanticFastSerializer]):
        auth = (TokenSyncAuth(header_name='X-Api-Key'),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.objects.create_token(
        user=admin_user,
        name='custom-header',
    )

    wrong_header_request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )
    wrong_header_response = _CustomHeaderController.as_view()(
        wrong_header_request,
    )
    assert wrong_header_response.status_code == HTTPStatus.UNAUTHORIZED

    request = dmr_rf.get(
        '/whatever/',
        headers={'X-Api-Key': raw_token},
    )
    response = _CustomHeaderController.as_view()(request)
    assert response.status_code == HTTPStatus.OK


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
def test_sync_token_auth_prefix_stripping(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures a custom prefix is required for `Authorization` auth."""

    @final
    class _PrefixController(Controller[PydanticFastSerializer]):
        auth = (TokenSyncAuth(header_name='Authorization', prefix='Token'),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.objects.create_token(
        user=admin_user,
        name='prefix-test',
        expires_at=None,
    )
    # Bare token without 'Token ' prefix → should be rejected
    bare_request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': raw_token},
    )
    bare_response = _PrefixController.as_view()(bare_request)
    assert bare_response.status_code == HTTPStatus.UNAUTHORIZED

    # Correctly prefixed → should succeed
    prefixed_request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': f'Token {raw_token}'},
    )
    prefixed_response = _PrefixController.as_view()(prefixed_request)
    assert prefixed_response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_sync_token_auth_revoked(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures a revoked token returns 401."""
    token, raw_token = Token.objects.create_token(
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
    _, raw_token = Token.objects.create_token(
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

    _, raw_token = Token.objects.create_token(
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
    auth = (TokenAsyncAuth(),)

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
    token, raw_token = await Token.objects.acreate_token(
        user=admin_user,
        name='async-test',
    )
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert isinstance(request_auth(request), TokenAsyncAuth)
    assert isinstance(request_auth(request, strict=True), TokenAsyncAuth)
    assert request_token(request) == token
    await token.arefresh_from_db()
    assert token.last_used_at is not None
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
    token, raw_token = await Token.objects.acreate_token(
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
    _, raw_token = await Token.objects.acreate_token(
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

    _, raw_token = await Token.objects.acreate_token(
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


@pytest.mark.django_db
def test_query_token_sync_auth_success(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures QueryTokenSyncAuth reads the token from the query string."""

    @final
    class _QueryController(Controller[PydanticFastSerializer]):
        auth = (QueryTokenSyncAuth(),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.objects.create_token(
        user=admin_user,
        name='query-test',
    )
    request = dmr_rf.get('/whatever/', data={'token': raw_token})

    response = _QueryController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_cookie_token_sync_auth_success(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures CookieTokenSyncAuth reads the token from a cookie."""

    @final
    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.objects.create_token(
        user=admin_user,
        name='cookie-test',
    )
    request = dmr_rf.get('/whatever/')
    request.COOKIES['token'] = raw_token

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_sync_token_auth_no_last_used_update(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures update_last_used=False skips the last_used_at write (sync)."""

    @final
    class _NoUpdateController(Controller[PydanticFastSerializer]):
        auth = (TokenSyncAuth(update_last_used=False),)

        def get(self) -> str:
            return 'authed'

    token, raw_token = Token.objects.create_token(
        user=admin_user,
        name='no-update-test',
    )
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )

    response = _NoUpdateController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    token.refresh_from_db()
    assert token.last_used_at is None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_token_auth_no_last_used_update(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures update_last_used=False skips the last_used_at write (async)."""

    @final
    class _NoUpdateAsyncController(Controller[PydanticFastSerializer]):
        auth = (TokenAsyncAuth(update_last_used=False),)

        async def get(self) -> str:
            return 'authed'

    token, raw_token = await Token.objects.acreate_token(
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

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    await token.arefresh_from_db()
    assert token.last_used_at is None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_query_token_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures QueryTokenAsyncAuth reads the token from the query string."""

    @final
    class _AsyncQueryController(Controller[PydanticFastSerializer]):
        auth = (QueryTokenAsyncAuth(),)

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await Token.objects.acreate_token(
        user=admin_user,
        name='async-query-test',
    )
    request = dmr_async_rf.get('/whatever/', data={'token': raw_token})

    response = await dmr_async_rf.wrap(_AsyncQueryController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_token_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures CookieTokenAsyncAuth reads the token from a cookie."""

    @final
    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await Token.objects.acreate_token(
        user=admin_user,
        name='async-cookie-test',
    )
    request = dmr_async_rf.get('/whatever/')
    request.COOKIES['token'] = raw_token

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


# -- Unit tests for auth class methods --


def test_token_model_returns_token_class() -> None:
    """token_model() returns the Token model for both sync and async auth."""
    assert TokenSyncAuth().token_model() is Token
    assert TokenAsyncAuth().token_model() is Token


def test_sync_check_token_passes_for_active_token() -> None:
    """check_token() does not raise when the token is active."""
    token = Token(expires_at=None, revoked_at=None)
    TokenSyncAuth().check_token(token)  # must not raise


def test_sync_check_token_raises_inactive() -> None:
    """check_token() raises NotAuthenticatedError when the token is inactive."""
    from dmr.exceptions import NotAuthenticatedError

    token = Token(revoked_at=dt.datetime.now(dt.UTC))
    with pytest.raises(NotAuthenticatedError):
        TokenSyncAuth().check_token(token)


@pytest.mark.asyncio
async def test_async_check_token_passes_active() -> None:
    """Async check_token() does not raise when the token is active."""
    token = Token(expires_at=None, revoked_at=None)
    await TokenAsyncAuth().check_token(token)  # must not raise


@pytest.mark.asyncio
async def test_async_check_token_raises_inactive() -> None:
    """Async check_token() raises NotAuthenticatedError for inactive tokens."""
    from dmr.exceptions import NotAuthenticatedError

    token = Token(revoked_at=dt.datetime.now(dt.UTC))
    with pytest.raises(NotAuthenticatedError):
        await TokenAsyncAuth().check_token(token)
