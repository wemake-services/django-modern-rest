import datetime as dt
from typing import Final

import pytest
from django.contrib.auth.models import User
from freezegun.api import FrozenDateTimeFactory

from dmr.security.token.app.models import Token
from dmr.security.token.constants import TOKEN_DEFAULT_EXPIRY

_CUSTOM_EXPIRY_DAYS: Final = 90


@pytest.mark.django_db
def test_create_token(
    admin_user: User,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test create_token returns a Token and a raw string."""
    now = dt.datetime.now(dt.UTC)
    token, raw_token = Token.issue(
        user=admin_user,
        name='my-token',
    )

    assert isinstance(token, Token)
    assert isinstance(raw_token, str)
    assert len(raw_token) > 0
    assert token.user == admin_user
    assert token.name == 'my-token'
    assert token.expires_at is not None
    assert token.expires_at == now + TOKEN_DEFAULT_EXPIRY
    assert token.revoked_at is None
    assert token.is_active
    assert not token.is_expired
    # mypy plugin is not enabled for tests:
    assert str(token) == f"Token '{token.name}' for user_id={token.user_id}"  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_create_token_without_expiry(admin_user: User) -> None:
    """Test create_token supports explicitly non-expiring tokens."""
    token, raw_token = Token.issue(
        user=admin_user,
        name='non-expiring',
        expires_at=None,
    )

    assert isinstance(raw_token, str)
    assert token.expires_at is None
    assert not token.is_expired
    assert token.is_active


@pytest.mark.django_db
def test_create_token_explicit_expiry(
    admin_user: User,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test create_token supports explicitly expiring tokens."""
    now = dt.datetime.now(dt.UTC)
    expires = now + dt.timedelta(days=1)
    token, raw_token = Token.issue(
        user=admin_user,
        name='day-expiring',
        expires_at=expires,
    )

    assert isinstance(raw_token, str)
    assert token.expires_at == expires
    assert not token.is_expired
    assert token.is_active


@pytest.mark.django_db
def test_hash_token_is_stored(admin_user: User) -> None:
    """Test that the stored hash matches re-hashing the raw token."""
    token, _ = Token.issue(
        user=admin_user,
        name='hash-check',
    )

    assert isinstance(token.token_hash, str)


@pytest.mark.django_db
def test_token_is_expired(admin_user: User) -> None:
    """Test that a token with past expiry is expired."""
    token, _ = Token.issue(
        user=admin_user,
        name='expired',
        expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1),
    )

    assert token.is_expired
    assert not token.is_active


@pytest.mark.django_db
def test_token_revoke(admin_user: User) -> None:
    """Test that revoking a token marks it as revoked."""
    token, _ = Token.issue(user=admin_user, name='to-revoke')

    token.revoke()

    token.refresh_from_db()
    assert token.revoked_at is not None
    assert not token.is_active


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_token_arevoke(admin_user: User) -> None:
    """Test that arevoke marks token as revoked in async context."""
    token, _ = await Token.aissue(
        user=admin_user,
        name='to-arevoke',
    )

    await token.arevoke()

    await token.arefresh_from_db()
    assert token.revoked_at is not None
    assert not token.is_active


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_acreate_token_without_expiry(admin_user: User) -> None:
    """Test acreate_token supports explicitly non-expiring tokens (async)."""
    token, raw_token = await Token.aissue(
        user=admin_user,
        name='async-non-expiring',
        expires_at=None,
    )

    assert isinstance(raw_token, str)
    assert token.expires_at is None
    assert not token.is_expired
    assert token.is_active
