import secrets
from http import HTTPStatus
from typing import Any

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.urls import reverse
from inline_snapshot import snapshot

from dmr.security.token import request_token
from dmr.security.token.token import TokenLikeSync
from dmr.test import DMRClient
from dmr.types import EMPTY


def _get_token_model() -> type[TokenLikeSync]:
    from server.apps.token_auth.models import (  # type: ignore[import-not-found]  # noqa: PLC0415
        CustomToken,
    )

    return CustomToken  # type: ignore[no-any-return]


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:token_auth:token_sync_auth'),
    ],
)
@pytest.mark.parametrize(
    'auth_header',
    [
        {'X-API-Token': ''},
        {'X-API-Token': ' '},
        {'X-API-Token': 'Bearer'},
        {'X-API-Token': secrets.token_urlsafe(32)},
        {'X-API-Token': 'Bearer token'},
        {'X-API-Token': 'NotBearer token'},
        {'X-API-Token': 'not a token'},
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
    """Ensures that wrong auth params produces the right result."""
    response = dmr_client.post(
        url,
        data='{}',
        headers={**auth_header},
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
        reverse('api:token_auth:token_sync_auth'),
    ],
)
@pytest.mark.parametrize(
    'expires_at',
    [
        None,
        EMPTY,
    ],
)
def test_valid_auth(
    dmr_client: DMRClient,
    admin_user: User,
    settings: LazySettings,
    *,
    url: str,
    expires_at: Any,
) -> None:
    """Ensures that correct token auth works."""
    _, raw_token = _get_token_model().issue(
        user=admin_user,
        name='test',
        expires_at=expires_at,
    )

    response = dmr_client.post(
        url,
        data='{}',
        headers={'X-API-Token': raw_token},
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'username': admin_user.username,
        'email': admin_user.email,
        'is_active': admin_user.is_active,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:token_auth:token_sync_auth'),
    ],
)
def test_revoked_token(
    dmr_client: DMRClient,
    admin_user: User,
    settings: LazySettings,
    *,
    url: str,
) -> None:
    """Ensures that correct token auth works."""
    token, raw_token = _get_token_model().issue(
        user=admin_user,
        name='test',
    )
    token.revoke()

    response = dmr_client.post(
        url,
        data='{}',
        headers={'X-API-Token': raw_token},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


def test_request_on_custom_model(admin_user: User) -> None:
    """Ensure that `sync` respects the token type."""
    request = HttpRequest()
    token, _ = _get_token_model().issue(user=admin_user, name='test')
    request.__dmr_token__ = token  # type: ignore[attr-defined]

    assert isinstance(
        request_token(request, sync=True, strict=True),
        type(token),
    )
    assert isinstance(
        request_token(request, sync=True),
        type(token),
    )
    with pytest.raises(TypeError, match='requested sync mode'):
        request_token(request, sync=False, strict=True)
    with pytest.raises(TypeError, match='requested sync mode'):
        request_token(request, sync=False)
