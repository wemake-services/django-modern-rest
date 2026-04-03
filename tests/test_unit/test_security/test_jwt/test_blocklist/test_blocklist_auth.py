import datetime as dt
import json
import secrets
from collections.abc import Sequence
from http import HTTPStatus
from typing import Any, Final, Protocol, TypedDict, Unpack, final

import pytest
from django.apps import apps
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic.serializer import PydanticSerializer
from dmr.security.jwt.auth import JWTAsyncAuth, JWTSyncAuth, get_jwt
from dmr.security.jwt.blocklist.auth import (
    JWTokenBlocklistAsyncMixin,
    JWTokenBlocklistSyncMixin,
)
from dmr.security.jwt.token import JWToken
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_EXP: Final = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
_JTI: Final = secrets.token_hex()


class _JWTokenKwargs(TypedDict, total=False):
    exp: dt.datetime
    iat: dt.datetime
    iss: str
    aud: str | Sequence[str]
    jti: str
    extras: dict[str, Any]
    leeway: int


def test_is_installed() -> None:
    """Ensure that blocklist is in installed apps list."""
    assert apps.is_installed('dmr.security.jwt.blocklist')


class _TokenBuilder(Protocol):
    def __call__(self, **kwargs: Unpack[_JWTokenKwargs]) -> str: ...


@pytest.fixture
def build_user_token(admin_user: User, settings: LazySettings) -> _TokenBuilder:
    """Token factory for tests."""

    def factory(**kwargs: Unpack[_JWTokenKwargs]) -> str:
        token = JWToken(
            sub=str(admin_user.pk),
            **kwargs,
        )

        return token.encode(secret=settings.SECRET_KEY, algorithm='HS256')

    return factory


class MyJWTSyncAuth(JWTokenBlocklistSyncMixin, JWTSyncAuth):
    """JWTSyncAuth with blocklist mixin."""


@final
class _BlocklistSyncController(Controller[PydanticSerializer]):
    @modify(auth=[MyJWTSyncAuth()])
    def get(self) -> str:
        assert isinstance(get_jwt(self.request), JWToken)
        return 'authed'


@pytest.mark.django_db
def test_add_to_blocklist(
    build_user_token: _TokenBuilder,
) -> None:
    """Ensure that blocklist method works."""
    token = build_user_token(exp=_EXP, jti=_JTI)
    auth = MyJWTSyncAuth()
    decoded_token = auth.decode_token(token)

    blocklisted_token, created = auth.blocklist(decoded_token)

    assert blocklisted_token.jti == decoded_token.jti
    assert blocklisted_token.expires_at == decoded_token.exp
    assert str(
        getattr(blocklisted_token.user, auth.user_id_field),
    ) == auth.claim_from_token(decoded_token)
    assert created is True

    assert auth.blocklist_model().objects.filter(jti=decoded_token.jti).exists()


@pytest.mark.django_db
def test_double_add_to_blacklist(
    build_user_token: _TokenBuilder,
) -> None:
    """Ensure that blocklist method add jti to db only in first run."""
    token = build_user_token(exp=_EXP, jti=_JTI)
    auth = MyJWTSyncAuth()
    decoded_token = auth.decode_token(token)

    auth.blocklist(decoded_token)
    _, created = auth.blocklist(decoded_token)

    assert created is False


@pytest.mark.django_db
def test_blocklist_sync_mixin_success(
    dmr_rf: DMRRequestFactory,
    build_user_token: _TokenBuilder,
) -> None:
    """Ensures that sync check_auth of tokenblocklist mixin works."""
    token = build_user_token(exp=_EXP, jti=_JTI)
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )

    response = _BlocklistSyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_blocklist_sync_mixin_unauthorized(
    dmr_rf: DMRRequestFactory,
    build_user_token: _TokenBuilder,
) -> None:
    """Ensures that sync check_auth of tokenblocklist mixin works."""
    token = build_user_token(exp=_EXP, jti=_JTI)
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )
    auth = MyJWTSyncAuth()
    decoded_token = auth.decode_token(token)

    auth.blocklist(decoded_token)

    response = _BlocklistSyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Not authenticated',
                'type': 'security',
            },
        ],
    })


class MyJWTAsyncAuth(JWTokenBlocklistAsyncMixin, JWTAsyncAuth):
    """JWTAsyncAuth with blocklist mixin."""


@final
class _BlocklistAsyncController(Controller[PydanticSerializer]):
    @modify(auth=[MyJWTAsyncAuth()])
    async def get(self) -> str:
        return 'authed'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_add_to_blocklist(
    build_user_token: _TokenBuilder,
) -> None:
    """Ensure that blocklist method works."""
    token = build_user_token(exp=_EXP, jti=_JTI)
    auth = MyJWTAsyncAuth()
    decoded_token = auth.decode_token(token)

    blocklisted_token, created = await auth.blocklist(decoded_token)

    assert blocklisted_token.jti == decoded_token.jti
    assert blocklisted_token.expires_at == decoded_token.exp
    assert str(
        getattr(blocklisted_token.user, auth.user_id_field),
    ) == auth.claim_from_token(decoded_token)
    assert created is True

    assert (
        await auth
        .blocklist_model()
        .objects.filter(
            jti=decoded_token.jti,
        )
        .aexists()
    )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_double_add_to_blacklist(
    build_user_token: _TokenBuilder,
) -> None:
    """Ensure that blocklist method add jti to db only in first run."""
    token = build_user_token(exp=_EXP, jti=_JTI)
    auth = MyJWTAsyncAuth()
    decoded_token = auth.decode_token(token)

    await auth.blocklist(decoded_token)
    _, created = await auth.blocklist(decoded_token)

    assert created is False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_blocklist_async_mixin_ok(
    dmr_async_rf: DMRAsyncRequestFactory,
    build_user_token: _TokenBuilder,
) -> None:
    """Ensures that async check_auth of tokenblocklist mixin works."""
    token = build_user_token(exp=_EXP, jti=_JTI)
    request = dmr_async_rf.get(
        '/whatever/',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )

    response = await dmr_async_rf.wrap(
        _BlocklistAsyncController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_blocklist_async_mixin_unauthorized(
    dmr_async_rf: DMRAsyncRequestFactory,
    build_user_token: _TokenBuilder,
) -> None:
    """Ensures that async check_auth of tokenblocklist mixin works."""
    token = build_user_token(exp=_EXP, jti=_JTI)
    request = dmr_async_rf.get(
        '/whatever/',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )
    auth = MyJWTAsyncAuth()
    decoded_token = auth.decode_token(token)

    await auth.blocklist(decoded_token)

    response = await dmr_async_rf.wrap(
        _BlocklistAsyncController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Not authenticated',
                'type': 'security',
            },
        ],
    })
