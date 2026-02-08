from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest.test import DMRClient


@pytest.fixture
def password(faker: Faker) -> str:
    """Create a password for a user."""
    return faker.password()


@pytest.fixture
def user(faker: Faker, password: str) -> User:
    """Create fake user for tests."""
    return User.objects.create_user(
        faker.unique.user_name(),
        faker.unique.email(),
        password,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:django_session_auth:django_session_sync'),
        reverse('api:django_session_auth:django_session_async'),
    ],
)
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:django_session_auth:user_session_sync'),
        reverse('api:django_session_auth:user_session_async'),
    ],
)
def test_correct_django_session(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    check_url: str,
) -> None:
    """Ensures that correct auth params fit."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.cookies[settings.SESSION_COOKIE_NAME]

    response = dmr_client.get(
        check_url,
        cookies=response.cookies,
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'user_id': str(user.pk)}


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:django_session_auth:django_session_sync'),
        reverse('api:django_session_auth:django_session_async'),
    ],
)
@pytest.mark.parametrize(
    'auth_params',
    [
        {'username': 'wrong', 'password': 'wrong'},
        {'username': None, 'password': 'wrong'},
        {'username': 'wrong', 'password': None},
    ],
)
@pytest.mark.parametrize(
    'headers',
    [
        {},
        {'Content-Type': 'application/json'},
    ],
)
def test_wrong_auth_params(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    auth_params: dict[str, str | None],
    headers: dict[str, str],
) -> None:
    """Ensures that incorrect auth raises 401."""
    response = dmr_client.post(
        url,
        data={
            'username': auth_params['username'] or user.username,
            'password': auth_params['password'] or password,
        },
        headers=headers,
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert not response.cookies
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
