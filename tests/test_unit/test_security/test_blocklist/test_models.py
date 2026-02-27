import datetime as dt
import secrets

import pytest
from django.contrib.auth.models import User
from faker import Faker

from dmr.security.blocklist.models import BlocklistedJWTToken

jti = secrets.token_hex()
expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)


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
        jti=jti,
        expires_at=expires_at,
    )


@pytest.mark.django_db
def test_token_user_field(token: BlocklistedJWTToken, user: User) -> None:
    """Test user field."""
    assert token.user == user


@pytest.mark.django_db
def test_token_jti_field(token: BlocklistedJWTToken) -> None:
    """Test jti field."""
    assert token.jti == jti


@pytest.mark.django_db
def test_token_expires_at_field(token: BlocklistedJWTToken) -> None:
    """Test expires_at field."""
    assert token.expires_at == expires_at


@pytest.mark.django_db
def test_token_str(token: BlocklistedJWTToken) -> None:
    """Test token str."""
    assert str(token) == f'Token for {token.user} {token.jti}'
