import datetime as dt
import json
import secrets
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Final, TypeAlias

import pytest
from django.http import HttpResponse, HttpResponseBase
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot
from typing_extensions import Sentinel

from dmr.test import DMRAsyncClient, DMRClient
from dmr.types import EMPTY

# Can't really import these from `server`:
_ApiToken: TypeAlias = Any
_ApiUser: TypeAlias = Any

#: Header mapping where `None` means "generate a value in the test body".
_AuthHeader: TypeAlias = dict[str, str | None]

_SYNC_URL: Final = reverse('api:token_custom_user:api_token_sync_auth')
_ASYNC_URL: Final = reverse('api:token_custom_user:api_token_async_auth')
_UNKNOWN_TOKEN_SIZE: Final = 32
_EXPIRY_VALUES: Final = (None, EMPTY)

#: `None` is replaced by a random unknown token, see `_resolve_headers`.
_WRONG_HEADERS: Final[tuple[_AuthHeader, ...]] = (
    {'X-API-Token': ''},
    {'X-API-Token': ' '},
    {'X-API-Token': None},
    {'Authorization': 'Bearer token'},
    {},
)


def _get_models() -> tuple[_ApiToken, _ApiUser]:
    from server.apps.token_custom_user.models import (  # type: ignore[import-not-found]  # noqa: PLC0415
        ApiToken,
        ApiUser,
    )

    return ApiToken, ApiUser


def _resolve_headers(auth_header: _AuthHeader) -> dict[str, str]:
    """Replace `None` placeholders with a random unknown token."""
    unknown_token = secrets.token_urlsafe(_UNKNOWN_TOKEN_SIZE)
    return {
        header: unknown_token if header_value is None else header_value
        for header, header_value in auth_header.items()
    }


@pytest.fixture
def api_user(faker: Faker) -> _ApiUser:
    """Create a user of the custom, non-`AUTH_USER_MODEL` type."""
    _, api_user_model = _get_models()
    return api_user_model.objects.create(username=faker.unique.user_name())


@pytest.fixture
def assert_not_authenticated() -> Callable[[HttpResponseBase], None]:
    """Assert that the response is the regular `401` problem detail."""

    def factory(response: HttpResponseBase) -> None:
        # Test clients are only typed to return `HttpResponseBase`:
        assert isinstance(response, HttpResponse), response
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
        assert response.headers['Content-Type'] == 'application/json'
        assert json.loads(response.content) == snapshot({
            'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
        })

    return factory


@pytest.mark.django_db
@pytest.mark.parametrize('expires_at', _EXPIRY_VALUES)
def test_sync_valid_auth(
    dmr_client: DMRClient,
    api_user: _ApiUser,
    *,
    expires_at: dt.datetime | Sentinel | None,
) -> None:
    """Ensures that sync auth works with a custom user model."""
    token_model, _ = _get_models()
    token, raw_token = token_model.issue(
        user=api_user,
        name='test',
        expires_at=expires_at,
    )
    saved_updated_at = token.updated_at

    response = dmr_client.get(_SYNC_URL, headers={'X-API-Token': raw_token})

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'username': api_user.username,
        'is_active': True,
    }
    token.refresh_from_db()  # `update_last_used` is enabled for this view
    assert token.last_used_at is not None
    assert token.updated_at > saved_updated_at


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('expires_at', _EXPIRY_VALUES)
async def test_async_valid_auth(
    dmr_async_client: DMRAsyncClient,
    api_user: _ApiUser,
    *,
    expires_at: dt.datetime | Sentinel | None,
) -> None:
    """Ensures that async auth works with a custom user model."""
    token_model, _ = _get_models()
    token, raw_token = await token_model.aissue(
        user=api_user,
        name='test',
        expires_at=expires_at,
    )
    saved_updated_at = token.updated_at

    response = await dmr_async_client.get(
        _ASYNC_URL,
        headers={'X-API-Token': raw_token},
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'username': api_user.username,
        'is_active': True,
    }
    await token.arefresh_from_db()  # `update_last_used` is enabled here too
    assert token.last_used_at is not None
    assert token.updated_at > saved_updated_at


@pytest.mark.django_db
@pytest.mark.parametrize('auth_header', _WRONG_HEADERS)
def test_sync_wrong_token_header(
    dmr_client: DMRClient,
    assert_not_authenticated: Callable[[HttpResponseBase], None],
    *,
    auth_header: _AuthHeader,
) -> None:
    """Ensures that wrong auth params produce the right result."""
    response = dmr_client.get(
        _SYNC_URL,
        headers=_resolve_headers(auth_header),
    )

    assert_not_authenticated(response)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('auth_header', _WRONG_HEADERS)
async def test_async_wrong_token_header(
    dmr_async_client: DMRAsyncClient,
    assert_not_authenticated: Callable[[HttpResponseBase], None],
    *,
    auth_header: _AuthHeader,
) -> None:
    """Ensures that wrong auth params produce the right result."""
    response = await dmr_async_client.get(
        _ASYNC_URL,
        headers=_resolve_headers(auth_header),
    )

    assert_not_authenticated(response)


@pytest.mark.django_db
def test_sync_revoked_token(
    dmr_client: DMRClient,
    api_user: _ApiUser,
    assert_not_authenticated: Callable[[HttpResponseBase], None],
) -> None:
    """Ensures that `revoke` invalidates the token."""
    token_model, _ = _get_models()
    token, raw_token = token_model.issue(user=api_user, name='test')
    token.revoke()

    response = dmr_client.get(_SYNC_URL, headers={'X-API-Token': raw_token})

    assert_not_authenticated(response)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_revoked_token(
    dmr_async_client: DMRAsyncClient,
    api_user: _ApiUser,
    assert_not_authenticated: Callable[[HttpResponseBase], None],
) -> None:
    """Ensures that `arevoke` invalidates the token."""
    token_model, _ = _get_models()
    token, raw_token = await token_model.aissue(user=api_user, name='test')
    await token.arevoke()

    response = await dmr_async_client.get(
        _ASYNC_URL,
        headers={'X-API-Token': raw_token},
    )

    assert_not_authenticated(response)


@pytest.mark.django_db
def test_sync_expired_token(
    dmr_client: DMRClient,
    api_user: _ApiUser,
    assert_not_authenticated: Callable[[HttpResponseBase], None],
) -> None:
    """Ensures that an expired token is rejected by sync auth."""
    token_model, _ = _get_models()
    _, raw_token = token_model.issue(
        user=api_user,
        name='test',
        expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
    )

    response = dmr_client.get(_SYNC_URL, headers={'X-API-Token': raw_token})

    assert_not_authenticated(response)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_expired_token(
    dmr_async_client: DMRAsyncClient,
    api_user: _ApiUser,
    assert_not_authenticated: Callable[[HttpResponseBase], None],
) -> None:
    """Ensures that an expired token is rejected by async auth."""
    token_model, _ = _get_models()
    _, raw_token = await token_model.aissue(
        user=api_user,
        name='test',
        expires_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
    )

    response = await dmr_async_client.get(
        _ASYNC_URL,
        headers={'X-API-Token': raw_token},
    )

    assert_not_authenticated(response)


@pytest.mark.django_db
def test_sync_inactive_user(
    dmr_client: DMRClient,
    api_user: _ApiUser,
    assert_not_authenticated: Callable[[HttpResponseBase], None],
) -> None:
    """Ensures that a token of an inactive user is rejected by sync auth."""
    token_model, _ = _get_models()
    _, raw_token = token_model.issue(user=api_user, name='test')
    api_user.is_active = False
    api_user.save(update_fields=['is_active'])

    response = dmr_client.get(_SYNC_URL, headers={'X-API-Token': raw_token})

    assert_not_authenticated(response)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_inactive_user(
    dmr_async_client: DMRAsyncClient,
    api_user: _ApiUser,
    assert_not_authenticated: Callable[[HttpResponseBase], None],
) -> None:
    """Ensures that a token of an inactive user is rejected by async auth."""
    token_model, _ = _get_models()
    _, raw_token = await token_model.aissue(user=api_user, name='test')
    api_user.is_active = False
    await api_user.asave(update_fields=['is_active'])

    response = await dmr_async_client.get(
        _ASYNC_URL,
        headers={'X-API-Token': raw_token},
    )

    assert_not_authenticated(response)
