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

from dmr.security.jwt.token import JWToken
from dmr.test import DMRClient

_OBTAIN_URLS: Final = (
    reverse('api:jwt_auth:jwt_cookie_obtain_sync'),
    reverse('api:jwt_auth:jwt_cookie_obtain_async'),
)
_REFRESH_URLS: Final = (
    reverse('api:jwt_auth:jwt_cookie_refresh_sync'),
    reverse('api:jwt_auth:jwt_cookie_refresh_async'),
)
_LOGOUT_URLS: Final = (
    reverse('api:jwt_auth:jwt_cookie_logout_sync'),
    reverse('api:jwt_auth:jwt_cookie_logout_async'),
)


@pytest.fixture
def dmr_client_csrf() -> DMRClient:
    """Test client that does enforce CSRF checks."""
    return DMRClient(enforce_csrf_checks=True)


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


@pytest.mark.django_db
@pytest.mark.parametrize('url', _OBTAIN_URLS)
def test_obtain_sets_cookies(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that a login sets both token cookies and nothing else."""
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
    assert _decode(access.value) == {
        'sub': str(user.pk),
        'exp': IsNumber(),
        'iat': IsNumber(),
        'jti': IsStr(),
        'extras': {'type': 'access'},
    }
    assert access['httponly']
    assert access['secure']
    assert access['samesite'] == 'lax'
    assert access['path'] == '/'
    assert access['max-age'] == int(dt.timedelta(days=1).total_seconds())

    refresh = response.cookies['refresh_token']
    assert _decode(refresh.value)['extras'] == {'type': 'refresh'}
    assert refresh['httponly']
    assert refresh['secure']
    assert refresh['samesite'] == 'lax'
    assert refresh['path'] == reverse('api:jwt_auth:jwt_cookie_refresh_sync')
    assert refresh['max-age'] == int(dt.timedelta(days=10).total_seconds())


@pytest.mark.django_db
@pytest.mark.parametrize('url', _OBTAIN_URLS)
def test_obtain_wrong_credentials(
    dmr_client: DMRClient,
    user: User,
    *,
    url: str,
) -> None:
    """Ensures that no cookies are set for a failed login."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': 'wrong-password'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert not response.cookies
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
@pytest.mark.parametrize('url', _OBTAIN_URLS)
def test_obtain_inactive_user(
    dmr_client: DMRClient,
    inactive_user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that inactive users get no cookies."""
    response = dmr_client.post(
        url,
        data={'username': inactive_user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert not response.cookies


@pytest.mark.django_db
@pytest.mark.parametrize('url', _OBTAIN_URLS)
def test_obtain_wrong_structure(
    dmr_client: DMRClient,
    *,
    url: str,
) -> None:
    """Ensures that an incorrect body raises 400."""
    response = dmr_client.post(url, data={'user': 'name'})

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert not response.cookies


@pytest.mark.django_db
def test_obtain_with_response_body(
    dmr_client: DMRClient,
    user: User,
    password: str,
) -> None:
    """Ensures that cookie views can also return a body."""
    response = dmr_client.post(
        reverse('api:jwt_auth:jwt_cookie_obtain_body'),
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == {
        'username': user.username,
        'email': user.email,
        'is_active': True,
    }
    assert 'access_token' in response.cookies


@pytest.mark.django_db
@pytest.mark.parametrize('check_url', _OBTAIN_URLS)
@pytest.mark.parametrize(
    'auth_url',
    [
        reverse('api:jwt_auth:jwt_cookie_sync_auth'),
        reverse('api:jwt_auth:jwt_cookie_async_auth'),
    ],
)
def test_obtained_cookie_authenticates(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    check_url: str,
    auth_url: str,
) -> None:
    """Ensures that the issued cookie is accepted by the cookie auth."""
    obtain_response = dmr_client.post(
        check_url,
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.NO_CONTENT

    response = dmr_client.get(auth_url)

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == {
        'username': user.username,
        'email': user.email,
        'is_active': True,
    }


@pytest.mark.django_db
@pytest.mark.parametrize('url', _REFRESH_URLS)
def test_refresh_rotates_cookies(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that the refresh cookie buys a new pair of cookies."""
    obtain_response = dmr_client.post(
        reverse('api:jwt_auth:jwt_cookie_obtain_sync'),
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.NO_CONTENT
    old_access = obtain_response.cookies['access_token'].value

    response = dmr_client.post(url)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.cookies.keys() == {'access_token', 'refresh_token'}

    new_access = response.cookies['access_token'].value
    assert _decode(new_access)['sub'] == str(user.pk)
    assert _decode(new_access)['jti'] != _decode(old_access)['jti']
    assert _decode(response.cookies['refresh_token'].value)['extras'] == {
        'type': 'refresh',
    }


@pytest.mark.django_db
@pytest.mark.parametrize('url', _REFRESH_URLS)
def test_refresh_without_cookie(
    dmr_client: DMRClient,
    *,
    url: str,
) -> None:
    """Ensures that a request without the refresh cookie raises 401."""
    response = dmr_client.post(url)

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert not response.cookies
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
@pytest.mark.parametrize('url', _REFRESH_URLS)
@pytest.mark.parametrize(
    ('token_type', 'expected_status'),
    [
        ('access', HTTPStatus.UNAUTHORIZED),
        ('refresh', HTTPStatus.NO_CONTENT),
    ],
)
def test_refresh_with_wrong_token(
    dmr_client: DMRClient,
    user: User,
    *,
    url: str,
    token_type: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures that an access token cannot be used to refresh."""
    dmr_client.cookies['refresh_token'] = JWToken(
        sub=str(user.pk),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        extras={'type': token_type},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    response = dmr_client.post(url)

    assert response.status_code == expected_status, response.content


@pytest.mark.django_db
@pytest.mark.parametrize('url', _REFRESH_URLS)
def test_refresh_inactive_user(
    dmr_client: DMRClient,
    inactive_user: User,
    *,
    url: str,
) -> None:
    """Ensures that an inactive user cannot refresh."""
    dmr_client.cookies['refresh_token'] = JWToken(
        sub=str(inactive_user.pk),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        extras={'type': 'refresh'},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    response = dmr_client.post(url)

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
@pytest.mark.parametrize('url', _LOGOUT_URLS)
def test_logout_drops_cookies(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that logout sends both cookies back empty and expired."""
    obtain_response = dmr_client.post(
        reverse('api:jwt_auth:jwt_cookie_obtain_sync'),
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.NO_CONTENT

    response = dmr_client.post(url)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.cookies.keys() == {'access_token', 'refresh_token'}
    for cookie in response.cookies.values():
        assert not cookie.value
        assert cookie['max-age'] == 0
    assert not dmr_client.cookies['access_token'].value
    assert not dmr_client.cookies['refresh_token'].value


@pytest.mark.django_db
@pytest.mark.parametrize('url', _LOGOUT_URLS)
def test_logout_without_cookies(
    dmr_client: DMRClient,
    *,
    url: str,
) -> None:
    """Ensures that logout works even when there is nothing to drop."""
    response = dmr_client.post(url)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.cookies.keys() == {'access_token', 'refresh_token'}


@pytest.mark.django_db
@pytest.mark.parametrize('url', _REFRESH_URLS + _LOGOUT_URLS)
def test_cookie_only_views_check_csrf(
    dmr_client_csrf: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that views acting on cookies alone are CSRF protected."""
    obtain_response = dmr_client_csrf.post(
        reverse('api:jwt_auth:jwt_cookie_obtain_sync'),
        data={'username': user.username, 'password': password},
    )
    assert obtain_response.status_code == HTTPStatus.NO_CONTENT

    response = dmr_client_csrf.post(url)

    assert response.status_code == HTTPStatus.FORBIDDEN, response.content
    assert not response.cookies
    assert response.json()['detail'][0]['msg'].startswith('CSRF Failed')


@pytest.mark.django_db
@pytest.mark.parametrize('url', _REFRESH_URLS + _LOGOUT_URLS)
def test_cookie_only_views_with_csrf_token(
    dmr_client_csrf: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
) -> None:
    """Ensures that the CSRF token issued on login is enough to pass."""
    obtain_response = dmr_client_csrf.post(
        reverse('api:jwt_auth:jwt_cookie_obtain_sync'),
        data={'username': user.username, 'password': password},
    )
    csrf_token = obtain_response.cookies[settings.CSRF_COOKIE_NAME].value

    response = dmr_client_csrf.post(
        url,
        headers={'X-CSRFToken': csrf_token},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.cookies.keys() == {'access_token', 'refresh_token'}
