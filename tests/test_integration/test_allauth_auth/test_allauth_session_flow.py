from http import HTTPStatus
from typing import Final

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRClient

_PROTECTED_URLS: Final = (
    reverse('api:allauth_auth:user_sync'),
    reverse('api:allauth_auth:user_async'),
)


@pytest.fixture
def password(faker: Faker) -> str:
    """Create a password for a user."""
    return faker.password()


@pytest.fixture
def user(faker: Faker, password: str) -> User:
    """Create fake user for tests."""
    return User.objects.create_user(
        username=faker.unique.user_name(),
        email=faker.unique.email(),
        password=password,
    )


@pytest.fixture
def session_token(
    dmr_client: DMRClient,
    user: User,
    password: str,
) -> str:
    """Log in through `django-allauth` and return its session token."""
    response = dmr_client.post(
        reverse('api:allauth_auth:login'),
        data={'username': user.username, 'password': password},
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK, response.content
    token = response.json()['meta']['session_token']
    assert isinstance(token, str)
    return token


@pytest.mark.django_db
@pytest.mark.parametrize('url', _PROTECTED_URLS)
def test_allauth_session_flow(
    dmr_client: DMRClient,
    user: User,
    session_token: str,
    *,
    url: str,
) -> None:
    """Ensures a token from `allauth`'s own login view authenticates us."""
    response = dmr_client.get(url, headers={'X-Session-Token': session_token})

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == snapshot({
        'username': user.username,
        'email': user.email,
        'is_active': True,
    })


@pytest.mark.django_db
@pytest.mark.parametrize('url', _PROTECTED_URLS)
def test_allauth_session_missing_token(
    dmr_client: DMRClient,
    *,
    url: str,
) -> None:
    """Ensures the protected endpoints reject requests without a token."""
    response = dmr_client.get(url)

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
@pytest.mark.parametrize('url', _PROTECTED_URLS)
def test_allauth_session_unknown_token(
    dmr_client: DMRClient,
    *,
    url: str,
) -> None:
    """Ensures an unknown token is rejected."""
    response = dmr_client.get(
        url,
        headers={'X-Session-Token': 'not-a-real-session-key'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
@pytest.mark.parametrize('url', _PROTECTED_URLS)
def test_allauth_session_after_logout(
    dmr_client: DMRClient,
    session_token: str,
    *,
    url: str,
) -> None:
    """Ensures the token stops working once `allauth` logs the user out."""
    logout = dmr_client.delete(
        reverse('api:allauth_auth:current_session'),
        headers={'X-Session-Token': session_token},
    )
    # `allauth` answers a logout with 401: there is no session anymore.
    assert logout.status_code == HTTPStatus.UNAUTHORIZED, logout.content

    response = dmr_client.get(url, headers={'X-Session-Token': session_token})

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
def test_allauth_login_wrong_password(
    dmr_client: DMRClient,
    user: User,
) -> None:
    """Ensures the external login view still rejects bad credentials."""
    response = dmr_client.post(
        reverse('api:allauth_auth:login'),
        data={'username': user.username, 'password': 'wrong-password'},
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
