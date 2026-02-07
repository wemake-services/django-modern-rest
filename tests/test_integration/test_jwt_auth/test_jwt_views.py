from http import HTTPStatus

import jwt
import pytest
from dirty_equals import IsNumber
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
        faker.user_name(),
        faker.email(),
        password,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:jwt_auth:jwt_obtain_access_refresh_sync'),
        reverse('api:jwt_auth:jwt_obtain_access_refresh_async'),
    ],
)
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:jwt_auth:jwt_sync_auth'),
        reverse('api:jwt_auth:jwt_async_auth'),
    ],
)
@pytest.mark.parametrize(
    'token_type',
    [
        'access_token',
        'refresh_token',
    ],
)
@pytest.mark.parametrize(
    'headers',
    [
        {},
        {'Content-Type': 'application/json'},
    ],
)
def test_correct_auth_params(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    check_url: str,
    token_type: str,
    headers: dict[str, str],
) -> None:
    """Ensures that correct auth params fit."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
        headers=headers,
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    response_body = response.json()
    assert jwt.decode(
        response_body['access_token'],
        key=settings.SECRET_KEY,
        algorithms=['HS256'],
    ) == {
        'sub': str(user.pk),
        'exp': IsNumber(),
        'iat': IsNumber(),
        'extras': {'type': 'access'},
    }
    assert jwt.decode(
        response_body['refresh_token'],
        key=settings.SECRET_KEY,
        algorithms=['HS256'],
    ) == {
        'sub': str(user.pk),
        'exp': IsNumber(),
        'iat': IsNumber(),
        'extras': {'type': 'refresh'},
    }

    # Assert that it roundtrips to the auth-protected controller:
    token = response_body[token_type]
    response = dmr_client.post(
        check_url,
        data='{}',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:jwt_auth:jwt_obtain_access_refresh_sync'),
        reverse('api:jwt_auth:jwt_obtain_access_refresh_async'),
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
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:jwt_auth:jwt_obtain_access_refresh_sync'),
        reverse('api:jwt_auth:jwt_obtain_access_refresh_async'),
    ],
)
@pytest.mark.parametrize(
    'auth_params',
    [
        {'username2': 'wrong', 'password': 'wrong'},
        {'username': 'wrong', 'pass': 'wrong'},
        {},
    ],
)
@pytest.mark.parametrize(
    'headers',
    [
        {},
        {'Content-Type': 'application/json'},
    ],
)
def test_wrong_auth_structure(
    dmr_client: DMRClient,
    user: User,
    *,
    url: str,
    auth_params: dict[str, str],
    headers: dict[str, str],
) -> None:
    """Ensures that incorrect body raises 400."""
    response = dmr_client.post(
        url,
        data=auth_params,
        headers=headers,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json()['detail']
