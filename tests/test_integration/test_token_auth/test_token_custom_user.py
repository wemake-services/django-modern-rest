import datetime as dt
import secrets
from http import HTTPStatus
from typing import Any

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRClient
from dmr.types import EMPTY

_SYNC_URL = reverse('api:token_custom_user:api_token_sync_auth')
_ASYNC_URL = reverse('api:token_custom_user:api_token_async_auth')


def _get_models() -> Any:
    from server.apps.token_custom_user.models import (  # type: ignore[import-not-found]  # noqa: PLC0415
        ApiToken,
        ApiUser,
    )

    return ApiToken, ApiUser


@pytest.fixture
def api_user(faker: Faker) -> Any:
    """Create a user of the custom, non-`AUTH_USER_MODEL` type."""
    _, api_user_model = _get_models()
    return api_user_model.objects.create(username=faker.unique.user_name())


@pytest.mark.django_db
@pytest.mark.parametrize('url', [_SYNC_URL, _ASYNC_URL])
@pytest.mark.parametrize('expires_at', [None, EMPTY])
def test_valid_auth(
    dmr_client: DMRClient,
    api_user: Any,
    *,
    url: str,
    expires_at: Any,
) -> None:
    """Ensures that both sync and async auth work with a custom user."""
    token_model, _ = _get_models()
    _, raw_token = token_model.issue(
        user=api_user,
        name='test',
        expires_at=expires_at,
    )

    response = dmr_client.get(url, headers={'X-API-Token': raw_token})

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'username': api_user.username,
        'is_active': True,
    }


@pytest.mark.django_db
@pytest.mark.parametrize('url', [_SYNC_URL, _ASYNC_URL])
def test_async_issued_token(
    dmr_client: DMRClient,
    api_user: Any,
    *,
    url: str,
) -> None:
    """Ensures that `aissue` produces a token both auth types accept."""
    token_model, _ = _get_models()
    _, raw_token = async_to_sync(token_model.aissue)(
        user=api_user,
        name='test',
    )

    response = dmr_client.get(url, headers={'X-API-Token': raw_token})

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.json() == {
        'username': api_user.username,
        'is_active': True,
    }


@pytest.mark.django_db
@pytest.mark.parametrize('url', [_SYNC_URL, _ASYNC_URL])
@pytest.mark.parametrize(
    'auth_header',
    [
        {'X-API-Token': ''},
        {'X-API-Token': ' '},
        {'X-API-Token': secrets.token_urlsafe(32)},  # noqa: WPS432
        {'Authorization': 'Bearer token'},
        {},
    ],
)
def test_wrong_token_header(
    dmr_client: DMRClient,
    *,
    url: str,
    auth_header: dict[str, str],
) -> None:
    """Ensures that wrong auth params produce the right result."""
    response = dmr_client.get(url, headers={**auth_header})

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.django_db
def test_sync_revoked_token(dmr_client: DMRClient, api_user: Any) -> None:
    """Ensures that `revoke` invalidates the token."""
    token_model, _ = _get_models()
    token, raw_token = token_model.issue(user=api_user, name='test')
    token.revoke()

    response = dmr_client.get(_SYNC_URL, headers={'X-API-Token': raw_token})

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
def test_async_revoked_token(dmr_client: DMRClient, api_user: Any) -> None:
    """Ensures that `arevoke` invalidates the token."""
    token_model, _ = _get_models()
    token, raw_token = token_model.issue(user=api_user, name='test')
    async_to_sync(token.arevoke)()

    response = dmr_client.get(_ASYNC_URL, headers={'X-API-Token': raw_token})

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
@pytest.mark.parametrize('url', [_SYNC_URL, _ASYNC_URL])
def test_expired_token(
    dmr_client: DMRClient,
    api_user: Any,
    *,
    url: str,
) -> None:
    """Ensures that an expired token is rejected."""
    token_model, _ = _get_models()
    _, raw_token = token_model.issue(
        user=api_user,
        name='test',
        expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
    )

    response = dmr_client.get(url, headers={'X-API-Token': raw_token})

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
@pytest.mark.parametrize('url', [_SYNC_URL, _ASYNC_URL])
def test_inactive_user(
    dmr_client: DMRClient,
    api_user: Any,
    *,
    url: str,
) -> None:
    """Ensures that a token of an inactive user is rejected."""
    token_model, _ = _get_models()
    _, raw_token = token_model.issue(user=api_user, name='test')
    api_user.is_active = False
    api_user.save(update_fields=['is_active'])

    response = dmr_client.get(url, headers={'X-API-Token': raw_token})

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content


@pytest.mark.django_db
@pytest.mark.parametrize('url', [_SYNC_URL, _ASYNC_URL])
def test_last_used_is_tracked(
    dmr_client: DMRClient,
    api_user: Any,
    *,
    url: str,
) -> None:
    """Ensures that `update_last_used` persists `last_used_at`."""
    token_model, _ = _get_models()
    token, raw_token = token_model.issue(user=api_user, name='test')
    assert token.last_used_at is None

    response = dmr_client.get(url, headers={'X-API-Token': raw_token})

    assert response.status_code == HTTPStatus.OK, response.content
    token.refresh_from_db()
    assert token.last_used_at is not None
