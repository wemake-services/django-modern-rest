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

_OBTAIN_URLS: Final = (
    reverse('api:token_auth:token_concrete_obtain_sync'),
    reverse('api:token_auth:token_concrete_obtain_async'),
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


def _get_custom_token_model() -> type[TokenLikeSync]:
    from server.apps.token_auth.models import (  # type: ignore[import-not-found]  # noqa: PLC0415
        CustomToken,
    )

    return CustomToken  # type: ignore[no-any-return]


@pytest.mark.django_db
def test_concrete_obtain_default_model(
    dmr_client: DMRClient,
    user: User,
    password: str,
) -> None:
    """Ensures that the concrete view issues a token of the default model."""
    response = dmr_client.post(
        _OBTAIN_URLS[1],
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Cache-Control'] == 'no-store'
    raw_token = response.json()['token']
    assert raw_token
    issued = Token.find_raw(raw_token)
    assert issued is not None
    assert issued.get_user() == user


@pytest.mark.django_db
def test_concrete_obtain_custom_model(
    dmr_client: DMRClient,
    user: User,
    password: str,
) -> None:
    """Ensures that the concrete view respects a custom ``token_cls``."""
    response = dmr_client.post(
        _OBTAIN_URLS[0],
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    raw_token = response.json()['token']
    assert raw_token
    assert Token.find_raw(raw_token) is None
    assert _get_custom_token_model().find_raw(raw_token)


@pytest.mark.django_db
def test_concrete_obtain_roundtrips_to_auth(
    dmr_client: DMRClient,
    user: User,
    password: str,
) -> None:
    """Ensures that the issued token authenticates the next request."""
    response = dmr_client.post(
        _OBTAIN_URLS[0],
        data={'username': user.username, 'password': password},
    )
    assert response.status_code == HTTPStatus.OK, response.content

    response = dmr_client.post(
        reverse('api:token_auth:token_sync_auth'),
        data='{}',
        headers={'X-API-Token': response.json()['token']},
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
    """Ensures that the concrete view rejects wrong credentials."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': 'wrong'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert 'Cache-Control' not in response.headers
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
