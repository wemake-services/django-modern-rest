import datetime as dt
import secrets
from typing import final

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from typing_extensions import override

from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token.app.models import Token
from dmr.security.token.views import (
    ObtainTokenAsyncController,
    ObtainTokenPayload,
    ObtainTokenResponse,
    ObtainTokenSyncController,
)


@final
class _SyncObtainController(
    ObtainTokenSyncController[
        PydanticFastSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
        User,
    ],
):
    token_cls = Token

    @override
    def convert_auth_payload(
        self, payload: ObtainTokenPayload
    ) -> ObtainTokenPayload:
        return payload

    @override
    def make_api_response(self) -> ObtainTokenResponse:
        return {'token': self.issue_token(user=self.request.user)}


@final
class _AsyncObtainController(
    ObtainTokenAsyncController[
        PydanticFastSerializer,
        ObtainTokenPayload,
        ObtainTokenResponse,
        User,
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
        return {'token': await self.issue_token(user=self.request.user)}


def test_make_token_name_returns_nonempty_string() -> None:
    """make_token_name() returns a non-empty hex string."""
    ctrl = _SyncObtainController()
    name = ctrl.make_token_name()

    assert isinstance(name, str)
    assert len(name) > 0


def test_make_token_name_is_unique() -> None:
    """Each call to make_token_name() returns a different value."""
    ctrl = _SyncObtainController()
    names = {ctrl.make_token_name() for _ in range(10)}

    assert len(names) == 10


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('token_salt', 'token_algorithm'),
    [
        ('custom_salt', 'sha512'),
        ('another_salt', 'sha256'),
    ],
)
def test_issue_token_with_custom_salt_and_algorithm(
    admin_user: User,
    *,
    token_salt: str,
    token_algorithm: str,
) -> None:
    """issue_token() with custom salt/algorithm produces a token findable with those params."""
    ctrl = _SyncObtainController()
    raw_token = ctrl.issue_token(
        user=admin_user,
        token_salt=token_salt,
        token_algorithm=token_algorithm,
    )

    assert Token.find_raw(
        raw_token, token_salt=token_salt, token_algorithm=token_algorithm
    )
    assert Token.find_raw(raw_token) is None


@pytest.mark.django_db
def test_issue_token_with_custom_secret(admin_user: User) -> None:
    """issue_token() with a custom secret hashes the token with that secret."""
    ctrl = _SyncObtainController()
    raw_token = ctrl.issue_token(user=admin_user, token_secret='my-secret')

    assert Token.find_raw(raw_token, token_secret='my-secret')
    assert Token.find_raw(raw_token, token_secret=None) is None


@pytest.mark.django_db
@pytest.mark.parametrize('token_size', [16, 32])
def test_issue_token_with_custom_size(
    admin_user: User, *, token_size: int
) -> None:
    """issue_token() with a custom token_size produces a raw token of the expected length."""
    ctrl = _SyncObtainController()
    raw_token = ctrl.issue_token(user=admin_user, token_size=token_size)

    assert len(raw_token) == len(secrets.token_urlsafe(token_size))


@pytest.mark.django_db
def test_issue_token_with_no_expiry(admin_user: User) -> None:
    """issue_token() with expires_at=None produces a non-expiring token."""
    ctrl = _SyncObtainController()
    raw_token = ctrl.issue_token(user=admin_user, expires_at=None)

    token = Token.find_raw(raw_token)
    assert token is not None
    assert token.expires_at is None


@pytest.mark.django_db
def test_issue_token_uses_class_salt_and_algorithm(admin_user: User) -> None:
    """Class-level token_salt and token_algorithm are used when not overridden per call."""

    class _CustomController(_SyncObtainController):
        token_salt = 'class_salt'
        token_algorithm = 'sha512'

    ctrl = _CustomController()
    raw_token = ctrl.issue_token(user=admin_user)

    assert Token.find_raw(
        raw_token, token_salt='class_salt', token_algorithm='sha512'
    )
    assert Token.find_raw(raw_token) is None


@pytest.mark.django_db
def test_issue_token_uses_class_token_expiration(admin_user: User) -> None:
    """Class-level token_expiration controls the default token lifetime."""

    class _CustomController(_SyncObtainController):
        token_expiration = dt.timedelta(hours=1)

    now = dt.datetime.now(dt.UTC)
    ctrl = _CustomController()
    raw_token = ctrl.issue_token(user=admin_user)

    token = Token.find_raw(raw_token)
    assert token is not None
    assert token.expires_at is not None
    assert (
        abs((token.expires_at - (now + dt.timedelta(hours=1))).total_seconds())
        < 5
    )


@pytest.mark.django_db
def test_set_request_attrs_sets_user_on_request(admin_user: User) -> None:
    """set_request_attrs() sets request.user to the given user."""
    ctrl = _SyncObtainController()
    request = HttpRequest()
    ctrl.set_request_attrs(request, admin_user)

    assert request.user == admin_user


# --- Async ---


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('token_salt', 'token_algorithm'),
    [
        ('custom_salt', 'sha512'),
        ('another_salt', 'sha256'),
    ],
)
async def test_async_issue_token_with_custom_salt_and_algorithm(
    admin_user: User,
    *,
    token_salt: str,
    token_algorithm: str,
) -> None:
    """Async issue_token() with custom salt/algorithm produces a token findable with those params."""
    ctrl = _AsyncObtainController()
    raw_token = await ctrl.issue_token(
        user=admin_user,
        token_salt=token_salt,
        token_algorithm=token_algorithm,
    )

    assert await Token.afind_raw(
        raw_token, token_salt=token_salt, token_algorithm=token_algorithm
    )
    assert await Token.afind_raw(raw_token) is None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_issue_token_uses_class_salt_and_algorithm(
    admin_user: User,
) -> None:
    """Class-level token_salt and token_algorithm are used in async issue_token()."""

    class _CustomController(_AsyncObtainController):
        token_salt = 'class_salt'
        token_algorithm = 'sha512'

    ctrl = _CustomController()
    raw_token = await ctrl.issue_token(user=admin_user)

    assert await Token.afind_raw(
        raw_token, token_salt='class_salt', token_algorithm='sha512'
    )
    assert await Token.afind_raw(raw_token) is None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_issue_token_uses_class_token_expiration(
    admin_user: User,
) -> None:
    """Class-level token_expiration controls the default token lifetime in async controller."""

    class _CustomController(_AsyncObtainController):
        token_expiration = dt.timedelta(hours=1)

    now = dt.datetime.now(dt.UTC)
    ctrl = _CustomController()
    raw_token = await ctrl.issue_token(user=admin_user)

    token = await Token.afind_raw(raw_token)
    assert token is not None
    assert token.expires_at is not None
    assert (
        abs((token.expires_at - (now + dt.timedelta(hours=1))).total_seconds())
        < 5
    )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_set_request_attrs_sets_user_on_request(
    admin_user: User,
) -> None:
    """set_request_attrs() sets request.user to the given user (async controller)."""
    ctrl = _AsyncObtainController()
    request = HttpRequest()
    await ctrl.set_request_attrs(request, admin_user)

    assert request.user == admin_user
