import datetime as dt
from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.security.jwt.token import JWToken
from dmr.test import DMRClient


@pytest.fixture
def user(faker: Faker) -> User:
    """Create fake user for tests."""
    return User.objects.create_user(
        username=faker.unique.user_name(),
        email=faker.unique.email(),
        password=faker.password(),
    )


@pytest.fixture
def access_token(user: User) -> str:
    """Encode a valid access token for the fake user."""
    return JWToken(
        sub=str(user.pk),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')


@pytest.mark.django_db
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:jwt_auth:jwt_cookie_sync_auth'),
        reverse('api:jwt_auth:jwt_cookie_async_auth'),
    ],
)
def test_jwt_cookie_auth(
    dmr_client: DMRClient,
    user: User,
    access_token: str,
    *,
    check_url: str,
) -> None:
    """Ensures that jwt cookie auth works end-to-end."""
    dmr_client.cookies['access_token'] = access_token

    response = dmr_client.get(check_url)

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == snapshot({
        'username': user.username,
        'email': user.email,
        'is_active': True,
    })


@pytest.mark.django_db
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:jwt_auth:jwt_cookie_sync_auth'),
        reverse('api:jwt_auth:jwt_cookie_async_auth'),
    ],
)
@pytest.mark.parametrize(
    'cookie_value',
    ['', 'not-a-token', 'Bearer {0}'],
)
def test_jwt_cookie_auth_invalid(
    dmr_client: DMRClient,
    access_token: str,
    *,
    check_url: str,
    cookie_value: str,
) -> None:
    """Ensures that malformed cookies are rejected."""
    dmr_client.cookies['access_token'] = cookie_value.format(access_token)

    response = dmr_client.get(check_url)

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:jwt_auth:jwt_cookie_sync_auth'),
        reverse('api:jwt_auth:jwt_cookie_async_auth'),
    ],
)
def test_jwt_cookie_auth_missing_cookie(
    dmr_client: DMRClient,
    *,
    check_url: str,
) -> None:
    """Ensures that a request without the cookie is not authed."""
    response = dmr_client.get(check_url)

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
