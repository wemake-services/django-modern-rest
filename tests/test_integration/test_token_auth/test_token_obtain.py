from http import HTTPStatus
from typing import Final

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.security.token.app.models import Token
from dmr.security.token.token import TokenLikeSync
from dmr.test import DMRClient

# Matches values from
# django_test_app/server/apps/token_auth/views/obtain.py
_SALT: Final = 'custom_salt'
_ALGO: Final = 'sha512'


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


def _get_token_model() -> type[TokenLikeSync]:
    from server.apps.token_auth.models import (  # type: ignore[import-not-found]  # noqa: PLC0415
        CustomToken,
    )

    return CustomToken  # type: ignore[no-any-return]


@pytest.mark.django_db
def test_full_e2e_sync(
    dmr_client: DMRClient,
    user: User,
    password: str,
) -> None:
    """Ensures that full pipeline with getting the token and auth works."""
    response = dmr_client.post(
        reverse('api:token_auth:token_obtain_async'),
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.headers['Cache-Control'] == 'no-store'
    response_json = response.json()
    assert response_json['token']
    assert Token.find_raw(
        response_json['token'],
        token_salt=_SALT,
        token_algorithm=_ALGO,
    )
    assert (
        _get_token_model().find_raw(
            response_json['token'],
            token_salt=_SALT,
            token_algorithm=_ALGO,
        )
        is None
    )

    response = dmr_client.get(
        reverse('api:token_auth:token_custom_sync_auth'),
        headers={'X-API-Token': response_json['token']},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'username': user.username}


@pytest.mark.django_db
def test_obtain_custom_token_model(
    dmr_client: DMRClient,
    user: User,
    password: str,
) -> None:
    """Ensures that custom user model works for the obtain view."""
    response = dmr_client.post(
        reverse('api:token_auth:token_obtain_sync'),
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.headers['Cache-Control'] == 'no-store'
    response_json = response.json()
    assert response_json['token']
    assert Token.find_raw(response_json['token']) is None
    assert _get_token_model().find_raw(response_json['token'])


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:token_auth:token_obtain_sync'),
        reverse('api:token_auth:token_obtain_async'),
    ],
)
def test_obtain_failures(
    dmr_client: DMRClient,
    user: User,
    *,
    url: str,
) -> None:
    """Ensures that wrong credentials fail the obtain pipeline."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': 'wrong'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert 'Cache-Control' not in response.headers
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
