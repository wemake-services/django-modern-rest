import datetime as dt
from http import HTTPStatus
from typing import Final

import jwt
import pytest
from dirty_equals import IsNumber, IsStr
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRClient

_OBTAIN_URLS: Final = (
    reverse('api:jwt_auth:jwt_concrete_obtain_sync'),
    reverse('api:jwt_auth:jwt_concrete_obtain_async'),
)
_REFRESH_URLS: Final = (
    reverse('api:jwt_auth:jwt_concrete_refresh_sync'),
    reverse('api:jwt_auth:jwt_concrete_refresh_async'),
)
_VERIFY_URLS: Final = (
    reverse('api:jwt_auth:jwt_concrete_verify_sync'),
    reverse('api:jwt_auth:jwt_concrete_verify_async'),
)
_COOKIE_OBTAIN_URLS: Final = (
    reverse('api:jwt_auth:jwt_concrete_cookie_obtain_sync'),
    reverse('api:jwt_auth:jwt_concrete_cookie_obtain_async'),
)
_COOKIE_REFRESH_URL: Final = reverse(
    'api:jwt_auth:jwt_concrete_cookie_refresh_sync',
)
#: Concrete cookie views leave `jwt_refresh_cookie_path` at its default.
_DEFAULT_REFRESH_COOKIE_PATH: Final = '/'
_COOKIE_LOGOUT_URL: Final = reverse(
    'api:jwt_auth:jwt_concrete_cookie_logout_sync',
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
def inactive_user(faker: Faker, password: str) -> User:
    """Create inactive fake user for tests."""
    return User.objects.create_user(
        username=faker.unique.user_name(),
        email=faker.unique.email(),
        password=password,
        is_active=False,
    )


def _decode(encoded_token: str) -> dict[str, object]:
    return jwt.decode(
        encoded_token,
        key=settings.SECRET_KEY,
        algorithms=['HS256'],
    )


def _claims(user: User, token_type: str) -> dict[str, object]:
    return {
        'sub': str(user.pk),
        'exp': IsNumber(),
        'iat': IsNumber(),
        'jti': IsStr(),
        'extras': {'type': token_type},
    }


@pytest.mark.django_db
@pytest.mark.parametrize('url', _OBTAIN_URLS)
@pytest.mark.parametrize(
    'check_url',
    [
        reverse('api:jwt_auth:jwt_sync_auth'),
        reverse('api:jwt_auth:jwt_async_auth'),
    ],
)
def test_concrete_obtain(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    check_url: str,
) -> None:
    """Ensures that the concrete obtain view issues usable tokens."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Cache-Control'] == 'no-store'
    response_body = response.json()
    assert _decode(response_body['access_token']) == _claims(user, 'access')
    assert _decode(response_body['refresh_token']) == _claims(user, 'refresh')

    # Assert that it roundtrips to the auth-protected controller:
    response = dmr_client.post(
        check_url,
        data='{}',
        headers={'Authorization': f'Bearer {response_body["access_token"]}'},
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.json() == {
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
    }


@pytest.mark.django_db
@pytest.mark.parametrize('url', _OBTAIN_URLS)
def test_concrete_obtain_wrong_password(
    dmr_client: DMRClient,
    user: User,
    *,
    url: str,
) -> None:
    """Ensures that the concrete obtain view rejects wrong credentials."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': 'wrong'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
@pytest.mark.parametrize('url', _OBTAIN_URLS)
def test_concrete_obtain_inactive_user(
    dmr_client: DMRClient,
    inactive_user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that the concrete obtain view rejects inactive users."""
    response = dmr_client.post(
        url,
        data={'username': inactive_user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
@pytest.mark.parametrize('url', _REFRESH_URLS)
@pytest.mark.parametrize('obtain_url', _OBTAIN_URLS)
def test_concrete_refresh(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    obtain_url: str,
) -> None:
    """Ensures that the concrete refresh view rotates both tokens."""
    obtain_response = dmr_client.post(
        obtain_url,
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.OK

    response = dmr_client.post(
        url,
        data={'refresh_token': obtain_response.json()['refresh_token']},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Cache-Control'] == 'no-store'
    response_body = response.json()
    assert _decode(response_body['access_token']) == _claims(user, 'access')
    assert _decode(response_body['refresh_token']) == _claims(user, 'refresh')


@pytest.mark.django_db
@pytest.mark.parametrize('url', _REFRESH_URLS)
def test_concrete_refresh_with_access_token(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that an access token is not accepted as a refresh one."""
    obtain_response = dmr_client.post(
        _OBTAIN_URLS[0],
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.OK

    response = dmr_client.post(
        url,
        data={'refresh_token': obtain_response.json()['access_token']},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
@pytest.mark.parametrize('url', _VERIFY_URLS)
@pytest.mark.parametrize('obtain_url', _OBTAIN_URLS)
def test_concrete_verify(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    obtain_url: str,
) -> None:
    """Ensures that the concrete verify view accepts a fresh access token."""
    obtain_response = dmr_client.post(
        obtain_url,
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.OK

    response = dmr_client.post(
        url,
        data={'access_token': obtain_response.json()['access_token']},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.content == b''


@pytest.mark.django_db
@pytest.mark.parametrize('url', _VERIFY_URLS)
def test_concrete_verify_with_refresh_token(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that a refresh token is not accepted as an access one."""
    obtain_response = dmr_client.post(
        _OBTAIN_URLS[0],
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.OK

    response = dmr_client.post(
        url,
        data={'access_token': obtain_response.json()['refresh_token']},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
@pytest.mark.parametrize('url', _COOKIE_OBTAIN_URLS)
def test_concrete_cookie_obtain(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that the concrete cookie view sets both token cookies."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.content == b''
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.cookies.keys() == {
        'access_token',
        'refresh_token',
        settings.CSRF_COOKIE_NAME,
    }

    access = response.cookies['access_token']
    assert _decode(access.value) == _claims(user, 'access')
    assert access['httponly']
    assert access['secure']
    assert access['path'] == '/'

    refresh = response.cookies['refresh_token']
    assert _decode(refresh.value) == _claims(user, 'refresh')
    assert refresh['httponly']
    assert refresh['secure']
    assert refresh['path'] == _DEFAULT_REFRESH_COOKIE_PATH
    assert refresh['max-age'] == int(dt.timedelta(days=10).total_seconds())


@pytest.mark.django_db
@pytest.mark.parametrize('url', _COOKIE_OBTAIN_URLS)
def test_concrete_cookie_refresh(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that the concrete cookie refresh rotates both cookies."""
    obtain_response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.NO_CONTENT
    original_refresh = obtain_response.cookies['refresh_token'].value

    response = dmr_client.post(_COOKIE_REFRESH_URL)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert _decode(response.cookies['access_token'].value) == _claims(
        user,
        'access',
    )
    assert response.cookies['refresh_token'].value != original_refresh


@pytest.mark.django_db
@pytest.mark.parametrize('url', _COOKIE_OBTAIN_URLS)
def test_concrete_cookie_logout(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that the concrete cookie logout drops both cookies."""
    obtain_response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.NO_CONTENT

    response = dmr_client.post(_COOKIE_LOGOUT_URL)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    for cookie_name in ('access_token', 'refresh_token'):
        assert not response.cookies[cookie_name].value
        assert response.cookies[cookie_name]['max-age'] == 0


@pytest.mark.django_db
def test_concrete_cookie_refresh_without_cookie(
    dmr_client: DMRClient,
) -> None:
    """Ensures that the concrete cookie refresh needs the refresh cookie."""
    response = dmr_client.post(_COOKIE_REFRESH_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
