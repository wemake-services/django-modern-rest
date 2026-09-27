from http import HTTPStatus
from typing import Final

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.security.token.app.models import Token
from dmr.security.token.token import (
    DEFAULT_TOKEN_ALGORITHM,
    DEFAULT_TOKEN_SALT,
    TokenLikeSync,
)
from dmr.test import DMRClient

# Matches values from
# django_test_app/server/apps/token_auth/views/obtain.py
_SALT: Final = 'custom_salt'
_ALGO: Final = 'sha512'

#: Customized reusable views and concrete views issue tokens the same way,
#: they only differ in the model and in the hashing settings.
#: The url, whether the model is `CustomToken`, the salt, and the algorithm:
_ISSUED_TOKENS: Final = (
    (
        reverse('api:token_auth:token_obtain_sync'),
        True,
        DEFAULT_TOKEN_SALT,
        DEFAULT_TOKEN_ALGORITHM,
    ),
    (
        reverse('api:token_auth:token_obtain_async'),
        False,
        _SALT,
        _ALGO,
    ),
    (
        reverse('api:token_auth:token_concrete_obtain_sync'),
        True,
        DEFAULT_TOKEN_SALT,
        DEFAULT_TOKEN_ALGORITHM,
    ),
    (
        reverse('api:token_auth:token_concrete_obtain_async'),
        False,
        DEFAULT_TOKEN_SALT,
        DEFAULT_TOKEN_ALGORITHM,
    ),
)
_OBTAIN_URLS: Final = tuple(issued[0] for issued in _ISSUED_TOKENS)


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
@pytest.mark.parametrize(
    ('url', 'is_custom_model', 'token_salt', 'token_algorithm'),
    _ISSUED_TOKENS,
)
def test_obtain_token(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    is_custom_model: bool,
    token_salt: str,
    token_algorithm: str,
) -> None:
    """Ensures that obtain views issue a token of their own model."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.headers['Cache-Control'] == 'no-store'
    raw_token = response.json()['token']
    token_model, other_model = (
        (_get_token_model(), Token)
        if is_custom_model
        else (Token, _get_token_model())
    )
    issued = token_model.find_raw(
        raw_token,
        token_salt=token_salt,
        token_algorithm=token_algorithm,
    )
    assert issued is not None
    assert issued.get_user() == user
    assert (
        other_model.find_raw(
            raw_token,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        )
        is None
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('url', 'auth_url'),
    [
        (
            reverse('api:token_auth:token_obtain_async'),
            reverse('api:token_auth:token_custom_sync_auth'),
        ),
        (
            reverse('api:token_auth:token_concrete_obtain_async'),
            reverse('api:token_auth:token_default_sync_auth'),
        ),
    ],
)
def test_obtained_token_authenticates(
    dmr_client: DMRClient,
    user: User,
    password: str,
    *,
    url: str,
    auth_url: str,
) -> None:
    """Ensures that full pipeline with getting the token and auth works."""
    response = dmr_client.post(
        url,
        data={'username': user.username, 'password': password},
    )
    assert response.status_code == HTTPStatus.OK, response.content

    response = dmr_client.get(
        auth_url,
        headers={'X-API-Token': response.json()['token']},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json()['username'] == user.username


@pytest.mark.django_db
@pytest.mark.parametrize('url', _OBTAIN_URLS)
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
