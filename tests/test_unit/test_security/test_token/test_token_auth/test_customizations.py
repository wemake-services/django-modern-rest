import datetime as dt
from typing import Final, TypeAlias

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest

from dmr.exceptions import NotAuthenticatedError
from dmr.security.token import (
    CookieTokenAsyncAuth,
    CookieTokenSyncAuth,
    HeaderTokenAsyncAuth,
    HeaderTokenSyncAuth,
    QueryTokenAsyncAuth,
    QueryTokenSyncAuth,
    request_token,
)
from dmr.security.token.app.models import Token

_TOKEN_SECRET: Final = 'custom-secret'  # noqa: S105
_TOKEN_SALT: Final = 'custom-salt'  # noqa: S105
_TOKEN_ALGORITHM: Final = 'sha512'  # noqa: S105
_SCHEME_NAME: Final = 'customToken'

_SyncAuthType: TypeAlias = (
    type[HeaderTokenSyncAuth]
    | type[CookieTokenSyncAuth]
    | type[QueryTokenSyncAuth]
)
_AsyncAuthType: TypeAlias = (
    type[HeaderTokenAsyncAuth]
    | type[CookieTokenAsyncAuth]
    | type[QueryTokenAsyncAuth]
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    'auth_type',
    [HeaderTokenSyncAuth, CookieTokenSyncAuth, QueryTokenSyncAuth],
)
def test_sync_auth_custom_hashing(
    auth_type: _SyncAuthType,
    admin_user: User,
) -> None:
    """Ensures each sync auth class forwards its token customizations."""
    token, raw_token = Token.issue(
        user=admin_user,
        name='sync-custom',
        token_secret=_TOKEN_SECRET,
        token_salt=_TOKEN_SALT,
        token_algorithm=_TOKEN_ALGORITHM,
    )
    auth = auth_type(
        security_scheme_name=_SCHEME_NAME,
        update_last_used=True,
        token_secret=_TOKEN_SECRET,
        token_salt=_TOKEN_SALT,
        token_algorithm=_TOKEN_ALGORITHM,
    )
    request = HttpRequest()

    user = auth.authenticate(request, raw_token)

    token.refresh_from_db()
    assert user == admin_user
    assert request.user == admin_user
    assert request_token(request) == token
    assert isinstance(token.last_used_at, dt.datetime)
    assert auth.security_requirement == {_SCHEME_NAME: []}


@pytest.mark.django_db
@pytest.mark.parametrize(
    'auth_type',
    [HeaderTokenSyncAuth, CookieTokenSyncAuth, QueryTokenSyncAuth],
)
@pytest.mark.parametrize(
    'customize_issue',
    [
        pytest.param(True, id='custom-issue-default-auth'),
        pytest.param(False, id='default-issue-custom-auth'),
    ],
)
def test_sync_auth_rejects_wrong_hashing(
    auth_type: _SyncAuthType,
    admin_user: User,
    *,
    customize_issue: bool,
) -> None:
    """Ensures mismatched sync issue and auth settings are rejected."""
    if customize_issue:
        _, raw_token = Token.issue(
            user=admin_user,
            name='sync-invalid',
            token_secret=_TOKEN_SECRET,
            token_salt=_TOKEN_SALT,
            token_algorithm=_TOKEN_ALGORITHM,
        )
        auth = auth_type()
    else:
        _, raw_token = Token.issue(
            user=admin_user,
            name='sync-invalid',
        )
        auth = auth_type(
            token_secret=_TOKEN_SECRET,
            token_salt=_TOKEN_SALT,
            token_algorithm=_TOKEN_ALGORITHM,
        )

    with pytest.raises(NotAuthenticatedError):
        auth.authenticate(HttpRequest(), raw_token)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    'auth_type',
    [HeaderTokenAsyncAuth, CookieTokenAsyncAuth, QueryTokenAsyncAuth],
)
async def test_async_auth_custom_hashing(
    auth_type: _AsyncAuthType,
    admin_user: User,
) -> None:
    """Ensures each async auth class forwards its token customizations."""
    token, raw_token = await Token.aissue(
        user=admin_user,
        name='async-custom',
        token_secret=_TOKEN_SECRET,
        token_salt=_TOKEN_SALT,
        token_algorithm=_TOKEN_ALGORITHM,
    )
    auth = auth_type(
        security_scheme_name=_SCHEME_NAME,
        update_last_used=True,
        token_secret=_TOKEN_SECRET,
        token_salt=_TOKEN_SALT,
        token_algorithm=_TOKEN_ALGORITHM,
    )
    request = HttpRequest()

    user = await auth.authenticate(request, raw_token)

    await token.arefresh_from_db()
    assert user == admin_user
    assert await request.auser() == admin_user
    assert request_token(request) == token
    assert isinstance(token.last_used_at, dt.datetime)
    assert auth.security_requirement == {_SCHEME_NAME: []}


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    'auth_type',
    [HeaderTokenAsyncAuth, CookieTokenAsyncAuth, QueryTokenAsyncAuth],
)
@pytest.mark.parametrize(
    'customize_issue',
    [
        pytest.param(True, id='custom-issue-default-auth'),
        pytest.param(False, id='default-issue-custom-auth'),
    ],
)
async def test_async_auth_rejects_wrong_hashing(
    auth_type: _AsyncAuthType,
    admin_user: User,
    *,
    customize_issue: bool,
) -> None:
    """Ensures mismatched async issue and auth settings are rejected."""
    if customize_issue:
        _, raw_token = await Token.aissue(
            user=admin_user,
            name='async-invalid',
            token_secret=_TOKEN_SECRET,
            token_salt=_TOKEN_SALT,
            token_algorithm=_TOKEN_ALGORITHM,
        )
        auth = auth_type()
    else:
        _, raw_token = await Token.aissue(
            user=admin_user,
            name='async-invalid',
        )
        auth = auth_type(
            token_secret=_TOKEN_SECRET,
            token_salt=_TOKEN_SALT,
            token_algorithm=_TOKEN_ALGORITHM,
        )

    with pytest.raises(NotAuthenticatedError):
        await auth.authenticate(HttpRequest(), raw_token)
