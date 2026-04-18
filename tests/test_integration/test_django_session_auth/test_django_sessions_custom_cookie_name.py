from http import HTTPStatus
from http.cookies import CookieError

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.urls import reverse
from faker import Faker

from dmr.test import DMRClient


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
    'cookie_name',
    [
        'dmr_sessions',
        'auth-token-id',
        'session_manager_id_for_production_env_0123456789',
    ],
)
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:django_session_auth:django_session_sync'),
        reverse('api:django_session_auth:django_session_async'),
    ],
)
def test_django_sessions_custom_cookie_name(
    dmr_client: DMRClient,
    user: User,
    password: str,
    settings: LazySettings,
    *,
    cookie_name: str,
    check_url: str,
) -> None:
    """Ensure that custom session cookie names are respected by the API."""
    settings.SESSION_COOKIE_NAME = cookie_name

    response = dmr_client.post(
        check_url,
        data={'username': user.username, 'password': password},
        content_type='application/json',
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.cookies[cookie_name]


@pytest.mark.django_db
@pytest.mark.parametrize(
    'invalid_cookie_name',
    [
        'session cookie',
        'session;id',
        '',
        '   ',
    ],
)
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:django_session_auth:django_session_sync'),
        reverse('api:django_session_auth:django_session_async'),
    ],
)
def test_django_sessions_wrong_cookie_name(
    dmr_client: DMRClient,
    user: User,
    password: str,
    settings: LazySettings,
    *,
    invalid_cookie_name: str,
    check_url: str,
) -> None:
    """Ensure that RFC-invalid cookie names raise a CookieError."""
    settings.SESSION_COOKIE_NAME = invalid_cookie_name
    with pytest.raises(
        CookieError,
        match=f'Illegal key {invalid_cookie_name!r}',
    ):
        dmr_client.post(
            check_url,
            data={'username': user.username, 'password': password},
            content_type='application/json',
        )
