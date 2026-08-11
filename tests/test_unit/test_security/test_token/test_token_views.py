import datetime as dt
import json
from http import HTTPStatus
from typing import Final, final

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token import HeaderTokenAsyncAuth, HeaderTokenSyncAuth
from dmr.security.token.app.models import Token
from dmr.security.token.views import (
    ObtainTokenAsyncController,
    ObtainTokenPayload,
    ObtainTokenResponse,
    ObtainTokenSyncController,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_USERNAME: Final = 'admin'
_PASSWORD: Final = 'password'  # noqa: S105
_WRONG_PASSWORD: Final = 'wrong'  # noqa: S105
_SYNC_TOKEN_SECRET: Final = 'sync-secret'  # noqa: S105
_SYNC_TOKEN_SALT: Final = 'sync-salt'  # noqa: S105
_SYNC_TOKEN_ALGORITHM: Final = 'sha512'  # noqa: S105
_SYNC_TOKEN_SIZE: Final = 24
_SYNC_TOKEN_LENGTH: Final = 32
_ASYNC_TOKEN_SECRET: Final = 'async-secret'  # noqa: S105
_ASYNC_TOKEN_SALT: Final = 'async-salt'  # noqa: S105
_ASYNC_TOKEN_ALGORITHM: Final = 'sha512'  # noqa: S105
_ASYNC_TOKEN_SIZE: Final = 20
_ASYNC_TOKEN_LENGTH: Final = 27
_WRONG_TOKEN_SECRET: Final = 'wrong-secret'  # noqa: S105
_WRONG_TOKEN_SALT: Final = 'wrong-salt'  # noqa: S105


@final
class _SyncObtainTokenController(
    ObtainTokenSyncController[
        PydanticFastSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
    ],
):
    token_cls = Token
    token_size = _SYNC_TOKEN_SIZE
    token_secret = _SYNC_TOKEN_SECRET
    token_salt = _SYNC_TOKEN_SALT
    token_algorithm = _SYNC_TOKEN_ALGORITHM
    token_expiration = dt.timedelta(minutes=5)

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokenPayload,
    ) -> ObtainTokenPayload:
        return payload

    @override
    def make_api_response(self) -> ObtainTokenResponse:
        return {'token': 'sync-response'}


@pytest.mark.django_db
def test_sync_obtain_token_login_success(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures sync login accepts valid credentials."""
    request = dmr_rf.post(
        '/whatever/',
        data={'username': _USERNAME, 'password': _PASSWORD},
    )

    response = _SyncObtainTokenController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'token': 'sync-response'}
    assert request.user == admin_user


@pytest.mark.django_db
def test_sync_obtain_token_login_failure(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures sync login rejects invalid credentials."""
    request = dmr_rf.post(
        '/whatever/',
        data={'username': _USERNAME, 'password': _WRONG_PASSWORD},
    )

    response = _SyncObtainTokenController.as_view()(request)

    assert admin_user.is_active
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@final
class _AsyncObtainTokenController(
    ObtainTokenAsyncController[
        PydanticFastSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
    ],
):
    token_cls = Token
    token_size = _ASYNC_TOKEN_SIZE
    token_secret = _ASYNC_TOKEN_SECRET
    token_salt = _ASYNC_TOKEN_SALT
    token_algorithm = _ASYNC_TOKEN_ALGORITHM
    token_expiration = dt.timedelta(minutes=10)

    @override
    async def convert_auth_payload(
        self,
        payload: ObtainTokenPayload,
    ) -> ObtainTokenPayload:
        return payload

    @override
    async def make_api_response(self) -> ObtainTokenResponse:
        return {'token': 'async-response'}


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_obtain_token_login_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures async login accepts valid credentials."""
    request = dmr_async_rf.post(
        '/whatever/',
        data={'username': _USERNAME, 'password': _PASSWORD},
    )

    response = await dmr_async_rf.wrap(
        _AsyncObtainTokenController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'token': 'async-response'}
    assert request.user == admin_user
    assert await request.auser() == admin_user


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_obtain_token_login_failure(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures async login rejects invalid credentials."""
    request = dmr_async_rf.post(
        '/whatever/',
        data={'username': _USERNAME, 'password': _WRONG_PASSWORD},
    )

    response = await dmr_async_rf.wrap(
        _AsyncObtainTokenController.as_view()(request),
    )

    assert admin_user.is_active
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_sync_issue_token_class_settings(admin_user: User) -> None:
    """Ensures sync token issue forwards controller-level customizations."""
    before = dt.datetime.now(dt.UTC)

    raw_token = _SyncObtainTokenController().issue_token(user=admin_user)

    token = Token.find_raw(
        raw_token,
        token_secret=_SyncObtainTokenController.token_secret,
        token_salt=_SyncObtainTokenController.token_salt,
        token_algorithm=_SyncObtainTokenController.token_algorithm,
    )
    assert token is not None
    assert Token.find_raw(raw_token) is None
    assert len(raw_token) == _SYNC_TOKEN_LENGTH
    assert token.user == admin_user
    assert len(token.name) == _SYNC_TOKEN_LENGTH
    assert token.expires_at is not None
    assert (
        before + _SyncObtainTokenController.token_expiration <= token.expires_at
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('token_secret', 'token_salt', 'token_algorithm'),
    [
        (_WRONG_TOKEN_SECRET, _SYNC_TOKEN_SALT, _SYNC_TOKEN_ALGORITHM),
        (_SYNC_TOKEN_SECRET, _WRONG_TOKEN_SALT, _SYNC_TOKEN_ALGORITHM),
        (_SYNC_TOKEN_SECRET, _SYNC_TOKEN_SALT, 'sha256'),
    ],
)
def test_sync_token_rejects_single_mismatch(
    admin_user: User,
    *,
    token_secret: str,
    token_salt: str,
    token_algorithm: str,
) -> None:
    """Ensures each mismatched sync hash setting prevents auth."""
    raw_token = _SyncObtainTokenController().issue_token(user=admin_user)
    auth = HeaderTokenSyncAuth(
        token_secret=token_secret,
        token_salt=token_salt,
        token_algorithm=token_algorithm,
    )

    with pytest.raises(NotAuthenticatedError):
        auth.authenticate(HttpRequest(), raw_token)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_issue_token_class_settings(admin_user: User) -> None:
    """Ensures async token issue forwards controller-level customizations."""
    raw_token = await _AsyncObtainTokenController().issue_token(
        user=admin_user,
        name='async-token',
        expires_at=None,
    )

    token = await Token.afind_raw(
        raw_token,
        token_secret=_AsyncObtainTokenController.token_secret,
        token_salt=_AsyncObtainTokenController.token_salt,
        token_algorithm=_AsyncObtainTokenController.token_algorithm,
    )
    assert token is not None
    assert await Token.afind_raw(raw_token) is None
    assert len(raw_token) == _ASYNC_TOKEN_LENGTH
    assert token.name == 'async-token'
    assert token.expires_at is None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('token_secret', 'token_salt', 'token_algorithm'),
    [
        (_WRONG_TOKEN_SECRET, _ASYNC_TOKEN_SALT, _ASYNC_TOKEN_ALGORITHM),
        (_ASYNC_TOKEN_SECRET, _WRONG_TOKEN_SALT, _ASYNC_TOKEN_ALGORITHM),
        (_ASYNC_TOKEN_SECRET, _ASYNC_TOKEN_SALT, 'sha256'),
    ],
)
async def test_async_token_rejects_single_mismatch(
    admin_user: User,
    *,
    token_secret: str,
    token_salt: str,
    token_algorithm: str,
) -> None:
    """Ensures each mismatched async hash setting prevents auth."""
    raw_token = await _AsyncObtainTokenController().issue_token(
        user=admin_user,
    )
    auth = HeaderTokenAsyncAuth(
        token_secret=token_secret,
        token_salt=token_salt,
        token_algorithm=token_algorithm,
    )

    with pytest.raises(NotAuthenticatedError):
        await auth.authenticate(HttpRequest(), raw_token)
