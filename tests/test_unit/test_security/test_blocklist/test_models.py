import datetime as dt
import secrets

import pytest
from django.contrib.auth.models import User
from faker import Faker

from dmr.security.blocklist.models import BlocklistedJWTToken

_JTI = secrets.token_hex()
_EXPIRES_AT = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)


@pytest.fixture
def user(faker: Faker) -> User:
    """Create fake user for tests."""
    return User.objects.create_user(
        faker.unique.user_name(),
        faker.unique.email(),
        faker.password(),
    )


@pytest.fixture
def token(user: User) -> BlocklistedJWTToken:
    """Create blocklisted token for tests."""
    return BlocklistedJWTToken.objects.create(
        user=user,
        jti=_JTI,
        expires_at=_EXPIRES_AT,
    )


@pytest.mark.django_db
def test_token_model_fields(token: BlocklistedJWTToken, user: User) -> None:
    """Test model fields."""
    assert token.user == user
    assert token.jti == _JTI
    assert token.expires_at == _EXPIRES_AT


@pytest.mark.django_db
def test_token_str(token: BlocklistedJWTToken) -> None:
    """Test token str."""
    assert str(token) == f'Blocked JWT token for {token.user} {token.jti}'
