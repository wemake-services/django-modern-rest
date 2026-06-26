import datetime as dt
from typing import Final

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User

from dmr.security.token.constants import TOKEN_DEFAULT_EXPIRY_DAYS
from dmr.security.token.logic import (
    token_acreate,
    token_arevoke,
    token_create,
    token_hash,
    token_is_active,
    token_is_expired,
    token_revoke,
)
from dmr.security.token.models import Token

_CUSTOM_EXPIRY_DAYS: Final = 90


@pytest.mark.django_db
def test_create_token(admin_user: User) -> None:
    """Test create_token returns a Token and a raw string."""
    before = dt.datetime.now(dt.UTC)
    token, raw_token = token_create(
        user=admin_user,
        name='my-token',
    )
    after = dt.datetime.now(dt.UTC)

    assert isinstance(token, Token)
    assert isinstance(raw_token, str)
    assert len(raw_token) > 0
    assert token.user == admin_user
    assert token.name == 'my-token'
    assert token.expires_at is not None
    assert (
        before + dt.timedelta(days=TOKEN_DEFAULT_EXPIRY_DAYS)
        <= token.expires_at
    )
    assert token.expires_at <= after + dt.timedelta(
        days=TOKEN_DEFAULT_EXPIRY_DAYS,
    )
    assert token.revoked_at is None
    assert token_is_active(token)


@pytest.mark.django_db
def test_create_token_without_expiry(admin_user: User) -> None:
    """Test create_token supports explicitly non-expiring tokens."""
    token, _ = token_create(
        user=admin_user,
        name='non-expiring',
        expires_at=None,
    )

    assert token.expires_at is None
    assert not token_is_expired(token)
    assert token_is_active(token)


@pytest.mark.django_db
def test_create_token_uses_custom_default_expiry(
    settings: LazySettings,
    admin_user: User,
) -> None:
    """Test create_token respects configurable default token expiry."""
    settings.DMR_SETTINGS = {
        'auth_token_default_expiry': dt.timedelta(days=_CUSTOM_EXPIRY_DAYS),
    }

    before = dt.datetime.now(dt.UTC)
    token, _ = token_create(
        user=admin_user,
        name='custom-default',
    )
    after = dt.datetime.now(dt.UTC)

    assert token.expires_at is not None
    assert before + dt.timedelta(days=_CUSTOM_EXPIRY_DAYS) <= token.expires_at
    assert token.expires_at <= after + dt.timedelta(days=_CUSTOM_EXPIRY_DAYS)


@pytest.mark.django_db
def test_create_token_uses_none_default_expiry(
    settings: LazySettings,
    admin_user: User,
) -> None:
    """Test create_token uses non-expiring default when configured with None."""
    settings.DMR_SETTINGS = {'auth_token_default_expiry': None}

    token, _ = token_create(user=admin_user, name='custom-none')
    assert token.expires_at is None


def test_hash_token_is_stable() -> None:
    """Test that hashing the same token twice gives the same result."""
    raw = 'some-raw-token'
    h1 = token_hash(raw)
    h2 = token_hash(raw)
    assert h1 == h2


@pytest.mark.django_db
def test_hash_token_is_stored(admin_user: User) -> None:
    """Test that the stored hash matches re-hashing the raw token."""
    token, raw_token = token_create(
        user=admin_user,
        name='hash-check',
    )

    assert token.token_hash == token_hash(raw_token)


@pytest.mark.django_db
def test_token_is_expired(admin_user: User) -> None:
    """Test that a token with past expiry is expired."""
    token, _ = token_create(
        user=admin_user,
        name='expired',
        expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1),
    )

    assert token_is_expired(token)
    assert not token_is_active(token)


@pytest.mark.django_db
def test_token_not_expired(admin_user: User) -> None:
    """Test that a token with future expiry is not expired."""
    token, _ = token_create(
        user=admin_user,
        name='valid',
        expires_at=dt.datetime.now(dt.UTC)
        + dt.timedelta(days=TOKEN_DEFAULT_EXPIRY_DAYS),
    )

    assert not token_is_expired(token)
    assert token_is_active(token)


@pytest.mark.django_db
def test_token_revoke(admin_user: User) -> None:
    """Test that revoking a token marks it as revoked."""
    token, _ = token_create(user=admin_user, name='to-revoke')

    token_revoke(token)

    assert token.revoked_at is not None
    assert not token_is_active(token)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_token_arevoke(admin_user: User) -> None:
    """Test that arevoke marks token as revoked in async context."""
    token, _ = await token_acreate(
        user=admin_user,
        name='to-arevoke',
    )

    await token_arevoke(token)

    assert token.revoked_at is not None
    assert not token_is_active(token)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_acreate_token_without_expiry(admin_user: User) -> None:
    """Test acreate_token supports explicitly non-expiring tokens (async)."""
    token, _ = await token_acreate(
        user=admin_user,
        name='async-non-expiring',
        expires_at=None,
    )

    assert token.expires_at is None
    assert not token_is_expired(token)
    assert token_is_active(token)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_acreate_token_uses_none_default_expiry(
    settings: LazySettings,
    admin_user: User,
) -> None:
    """Test acreate_token respects None default expiry setting (async)."""
    settings.DMR_SETTINGS = {'auth_token_default_expiry': None}

    token, _ = await token_acreate(
        user=admin_user,
        name='async-custom-none',
    )
    assert token.expires_at is None
