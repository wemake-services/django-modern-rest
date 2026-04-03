import datetime as dt
import secrets

import pytest
from django.contrib.auth.models import User

from dmr.security.jwt.blocklist.models import BlocklistedJWToken

_JTI = secrets.token_hex()
_EXPIRES_AT = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)


@pytest.fixture
def token(admin_user: User) -> BlocklistedJWToken:
    """Create blocklisted token for tests."""
    return BlocklistedJWToken.objects.create(
        user=admin_user,
        jti=_JTI,
        expires_at=_EXPIRES_AT,
    )


@pytest.mark.django_db
def test_token_model_fields(
    token: BlocklistedJWToken,
    admin_user: User,
) -> None:
    """Test model fields."""
    assert token.user == admin_user
    assert token.jti == _JTI
    assert token.expires_at == _EXPIRES_AT


@pytest.mark.django_db
def test_token_str(token: BlocklistedJWToken) -> None:
    """Test token str."""
    assert str(token) == f'Blocked JWT token for {token.user} {token.jti}'
