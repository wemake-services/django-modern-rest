from http import HTTPStatus
from typing import Final

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRClient

_LOGIN_URLS: Final = (
    reverse('api:django_session_auth:django_session_concrete_sync'),
    reverse('api:django_session_auth:django_session_concrete_async'),
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


@pytest.mark.django_db
@pytest.mark.parametrize('url', _LOGIN_URLS)
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:django_session_auth:user_session_sync'),
        reverse('api:django_session_auth:user_session_async'),
    ],
)
def test_concrete_session_login(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    check_url: str,
) -> None:
    """Ensures that the concrete session view logs a user in."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.json() == {'user_id': str(user.pk)}
    assert settings.SESSION_COOKIE_NAME in response.cookies

    # Assert that the session cookie roundtrips to a protected controller:
    response = dmr_client.get(check_url)

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == {'user_id': str(user.pk)}


@pytest.mark.django_db
@pytest.mark.parametrize('url', _LOGIN_URLS)
def test_concrete_session_wrong_password(
    dmr_client: DMRClient,
    user: User,
    *,
    url: str,
) -> None:
    """Ensures that the concrete session view rejects wrong credentials."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': 'wrong'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert 'Cache-Control' not in response.headers
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
@pytest.mark.parametrize('url', _LOGIN_URLS)
def test_concrete_session_wrong_structure(
    dmr_client: DMRClient,
    *,
    url: str,
) -> None:
    """Ensures that the concrete session view validates the request body."""
    response = dmr_client.post(url, data={'login': 'wrong'})

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.json()['detail']
