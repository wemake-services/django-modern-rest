import datetime as dt
from typing import Final, final
from unittest.mock import AsyncMock, Mock

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token import views as token_views
from dmr.security.token.app.models import Token
from dmr.security.token.views import (
    ObtainTokenAsyncController,
    ObtainTokenPayload,
    ObtainTokenResponse,
    ObtainTokenSyncController,
)

_PASSWORD: Final = 'secret'  # noqa: S105
_WRONG_PASSWORD: Final = 'wrong'  # noqa: S105
_TOKEN_SECRET: Final = 'test-secret'  # noqa: S105
_TOKEN_SALT: Final = 'test-salt'  # noqa: S105
_TOKEN_ALGORITHM: Final = 'sha512'  # noqa: S105
_SYNC_TOKEN_SIZE: Final = 24
_SYNC_TOKEN_LENGTH: Final = 32
_ASYNC_TOKEN_SIZE: Final = 20
_ASYNC_TOKEN_LENGTH: Final = 27


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
    token_secret = _TOKEN_SECRET
    token_salt = _TOKEN_SALT
    token_algorithm = _TOKEN_ALGORITHM
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


@final
class _AsyncObtainTokenController(
    ObtainTokenAsyncController[
        PydanticFastSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
    ],
):
    token_cls = Token

    @override
    async def convert_auth_payload(
        self,
        payload: ObtainTokenPayload,
    ) -> ObtainTokenPayload:
        return payload

    @override
    async def make_api_response(self) -> ObtainTokenResponse:
        return {'token': 'async-response'}


def _setup_controller(
    controller: _SyncObtainTokenController | _AsyncObtainTokenController,
) -> HttpRequest:
    request = HttpRequest()
    controller.setup(request)
    return request


@pytest.mark.django_db
def test_sync_obtain_token_login_success(
    monkeypatch: pytest.MonkeyPatch,
    admin_user: User,
) -> None:
    """Ensures sync login forwards credentials and authenticates the request."""
    controller = _SyncObtainTokenController()
    request = _setup_controller(controller)
    authenticate = Mock(return_value=admin_user)
    monkeypatch.setattr(token_views, 'authenticate', authenticate)
    payload = ObtainTokenPayload(username='admin', password=_PASSWORD)

    response = controller.post(payload)

    assert response == {'token': 'sync-response'}
    authenticate.assert_called_once_with(request, **payload)
    assert request.user is admin_user


@pytest.mark.django_db
def test_sync_obtain_token_login_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures sync login rejects invalid credentials."""
    controller = _SyncObtainTokenController()
    _setup_controller(controller)
    monkeypatch.setattr(token_views, 'authenticate', Mock(return_value=None))

    with pytest.raises(NotAuthenticatedError):
        controller.login(
            ObtainTokenPayload(username='admin', password=_WRONG_PASSWORD),
        )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_obtain_token_login_success(
    monkeypatch: pytest.MonkeyPatch,
    admin_user: User,
) -> None:
    """Ensures async login forwards credentials and authenticates request."""
    controller = _AsyncObtainTokenController()
    request = _setup_controller(controller)
    authenticate = AsyncMock(return_value=admin_user)
    monkeypatch.setattr(token_views, 'aauthenticate', authenticate)
    payload = ObtainTokenPayload(username='admin', password=_PASSWORD)

    response = await controller.post(payload)

    assert response == {'token': 'async-response'}
    authenticate.assert_awaited_once_with(request, **payload)
    assert request.user is admin_user
    assert await request.auser() is admin_user


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_obtain_token_login_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures async login rejects invalid credentials."""
    controller = _AsyncObtainTokenController()
    _setup_controller(controller)
    monkeypatch.setattr(
        token_views,
        'aauthenticate',
        AsyncMock(return_value=None),
    )

    with pytest.raises(NotAuthenticatedError):
        await controller.login(
            ObtainTokenPayload(username='admin', password=_WRONG_PASSWORD),
        )


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
    assert len(raw_token) == _SYNC_TOKEN_LENGTH
    assert token.user == admin_user
    assert len(token.name) == _SYNC_TOKEN_LENGTH
    assert token.expires_at is not None
    assert (
        before + _SyncObtainTokenController.token_expiration <= token.expires_at
    )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_issue_token_uses_call_settings(admin_user: User) -> None:
    """Ensures async token issue forwards call-level customizations."""
    raw_token = await _AsyncObtainTokenController().issue_token(
        user=admin_user,
        name='async-token',
        expires_at=None,
        token_size=_ASYNC_TOKEN_SIZE,
        token_secret=_TOKEN_SECRET,
        token_salt=_TOKEN_SALT,
        token_algorithm=_TOKEN_ALGORITHM,
    )

    token = await Token.afind_raw(
        raw_token,
        token_secret=_TOKEN_SECRET,
        token_salt=_TOKEN_SALT,
        token_algorithm=_TOKEN_ALGORITHM,
    )
    assert token is not None
    assert len(raw_token) == _ASYNC_TOKEN_LENGTH
    assert token.name == 'async-token'
    assert token.expires_at is None
