import datetime as dt
from http import HTTPStatus

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.urls import reverse
from inline_snapshot import snapshot

from dmr.security.jwt import JWToken
from dmr.test import DMRClient


@pytest.mark.parametrize(
    'url',
    [
        reverse('api:jwt_auth:jwt_sync_auth'),
        reverse('api:jwt_auth:jwt_async_auth'),
    ],
)
@pytest.mark.parametrize(
    'auth_header',
    [
        {'Authorization': ''},
        {'Authorization': ' '},
        {'Authorization': 'Bearer'},
        {'Authorization': 'Bearer token'},
        {'Authorization': 'NotBearer token'},
        {'Authorization': 'not a token'},
        {'Other': 'Bearer token'},
        {},
    ],
)
def test_wrong_jwt_header(
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
        reverse('api:jwt_auth:jwt_sync_auth'),
        reverse('api:jwt_auth:jwt_async_auth'),
    ],
)
def test_valid_auth(
    dmr_client: DMRClient,
    admin_user: User,
    settings: LazySettings,
    *,
    url: str,
) -> None:
    """Ensures that correct jwt auth works."""
    token = JWToken(
        sub=str(admin_user.pk),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    ).encode(settings.SECRET_KEY, algorithm='HS256')
    response = dmr_client.post(
        url,
        data='{}',
        headers={
            'Authorization': f'Bearer {token}',
        },
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
        reverse('api:jwt_auth:jwt_sync_auth'),
        reverse('api:jwt_auth:jwt_async_auth'),
    ],
)
def test_missing_user(
    dmr_client: DMRClient,
    settings: LazySettings,
    *,
    url: str,
) -> None:
    """Ensures that missing user raises."""
    token = JWToken(
        sub='-1',
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    ).encode(settings.SECRET_KEY, algorithm='HS256')
    response = dmr_client.post(
        url,
        data='{}',
        headers={
            'Authorization': f'Bearer {token}',
        },
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
        reverse('api:jwt_auth:jwt_sync_auth'),
        reverse('api:jwt_auth:jwt_async_auth'),
    ],
)
def test_inactive_user(
    dmr_client: DMRClient,
    settings: LazySettings,
    admin_user: User,
    *,
    url: str,
) -> None:
    """Ensures that missing user raises."""
    admin_user.is_active = False
    admin_user.save(update_fields=['is_active'])

    token = JWToken(
        sub=str(admin_user.pk),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    ).encode(settings.SECRET_KEY, algorithm='HS256')
    response = dmr_client.post(
        url,
        data='{}',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
