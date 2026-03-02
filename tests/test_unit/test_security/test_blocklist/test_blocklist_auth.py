import datetime as dt
import json
import secrets
from collections.abc import Callable, Sequence
from http import HTTPStatus
from typing import Any, Final, TypeAlias, TypedDict, Unpack, final

import pytest
from django.apps import apps
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from dmr import Controller, modify
from dmr.plugins.pydantic.serializer import PydanticSerializer
from dmr.security.blocklist.auth import (
    JWTTokenBlocklistAsyncMixin,
    JWTTokenBlocklistSyncMixin,
)
from dmr.security.jwt.auth import JWTAsyncAuth, JWTSyncAuth
from dmr.security.jwt.token import JWTToken
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_EXP: Final = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
_JTI: Final = secrets.token_hex()


class _JWTTokenKwargs(TypedDict, total=False):
    exp: dt.datetime
    iat: dt.datetime
    iss: str
    aud: str | Sequence[str]
    jti: str
    extras: dict[str, Any]
    leeway: int


def test_is_installed() -> None:
    """Ensure that blocklist is in installed apps list."""
    assert apps.is_installed('dmr.security.blocklist')


@pytest.fixture
def user(faker: Faker) -> User:
    """Create fake user for tests."""
    return User.objects.create_user(
        faker.unique.user_name(),
        faker.unique.email(),
        faker.password(),
    )


_TokenBuilder: TypeAlias = Callable[..., str]


@pytest.fixture
def build_user_token(user: User, settings: LazySettings) -> _TokenBuilder:
    """Token factory for tests."""

    def factory(**kwargs: Unpack[_JWTTokenKwargs]) -> str:
        token = JWTToken(
            sub=str(user.pk),
            **kwargs,
        )

        return token.encode(secret=settings.SECRET_KEY, algorithm='HS256')

    return factory


class MyJWTSyncAuth(JWTTokenBlocklistSyncMixin, JWTSyncAuth):
    """JWTSyncAuth with blocklist mixin."""


@final
class _BlocklistSyncController(Controller[PydanticSerializer]):
    @modify(auth=[MyJWTSyncAuth()])
    def get(self) -> str:
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

    assert auth.blocklist_model.objects.filter(jti=decoded_token.jti).exists()


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


class MyJWTAsyncAuth(JWTTokenBlocklistAsyncMixin, JWTAsyncAuth):
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

    assert await auth.blocklist_model.objects.filter(
        jti=decoded_token.jti,
    ).aexists()


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
