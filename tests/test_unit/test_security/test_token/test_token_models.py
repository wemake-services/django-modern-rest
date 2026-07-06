import datetime as dt
import secrets

import pytest
from django.contrib.auth.models import User

from dmr.security.token.models import Token

_TOKEN_HASH_SIZE = 32
_TOKEN_HASH = secrets.token_hex(_TOKEN_HASH_SIZE)
_EXPIRES_AT = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)


@pytest.fixture
def token(admin_user: User) -> Token:
    """Create a token model instance for tests."""
    return Token.objects.create(
        user=admin_user,
        name='my-token',
        token_hash=_TOKEN_HASH,
        expires_at=_EXPIRES_AT,
    )


@pytest.mark.django_db
def test_token_model_fields(
    token: Token,
    admin_user: User,
) -> None:
    """Test model fields."""
    assert token.user == admin_user
    assert token.name == 'my-token'
    assert token.token_hash == _TOKEN_HASH
    assert token.expires_at == _EXPIRES_AT
    assert token.revoked_at is None


@pytest.mark.django_db
def test_token_str(token: Token) -> None:
    """Test model string representation."""
    assert str(token) == f'Token "{token.name}" for {token.user}'
