import datetime as dt
import secrets
from http import HTTPStatus
from typing import Final

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpResponse
from typing_extensions import override

from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt.blocklist.auth import (
    JWTokenBlocklistAsyncMixin,
    JWTokenBlocklistSyncMixin,
)
from dmr.security.jwt.token import JWToken
from dmr.security.jwt.views import (
    CookieRefreshTokensAsyncController,
    CookieRefreshTokensSyncController,
    ObtainTokensResponse,
    RefreshTokenAsyncController,
    RefreshTokenPayload,
    RefreshTokenSyncController,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_REFRESH_PATH: Final = '/api/auth/refresh/'


class _CookieRefreshSyncController(
    JWTokenBlocklistSyncMixin,
    CookieRefreshTokensSyncController[PydanticFastSerializer],
):
    jwt_refresh_cookie_path = _REFRESH_PATH
    jwt_ensure_csrf = False


class _CookieRefreshAsyncController(
    JWTokenBlocklistAsyncMixin,
    CookieRefreshTokensAsyncController[PydanticFastSerializer],
):
    jwt_refresh_cookie_path = _REFRESH_PATH
    jwt_ensure_csrf = False


class _BodyRefreshSyncController(
    JWTokenBlocklistSyncMixin,
    RefreshTokenSyncController[
        PydanticFastSerializer,
        RefreshTokenPayload,
        ObtainTokensResponse,
    ],
):
    @override
    def convert_refresh_payload(self, payload: RefreshTokenPayload) -> str:
        return payload['refresh_token']

    @override
    def make_api_response(self) -> ObtainTokensResponse:
        return {
            'access_token': self.create_jwt_token(
                token_type='access',  # noqa: S106
            ),
            'refresh_token': self.create_jwt_token(
                token_type='refresh',  # noqa: S106
            ),
        }


class _BodyRefreshAsyncController(
    JWTokenBlocklistAsyncMixin,
    RefreshTokenAsyncController[
        PydanticFastSerializer,
        RefreshTokenPayload,
        ObtainTokensResponse,
    ],
):
    @override
    async def convert_refresh_payload(
        self,
        payload: RefreshTokenPayload,
    ) -> str:
        return payload['refresh_token']

    @override
    async def make_api_response(self) -> ObtainTokensResponse:
        return {
            'access_token': self.create_jwt_token(
                token_type='access',  # noqa: S106
            ),
            'refresh_token': self.create_jwt_token(
                token_type='refresh',  # noqa: S106
            ),
        }


@pytest.fixture
def refresh_token(admin_user: User) -> JWToken:
    """Refresh token of the test user."""
    return JWToken(
        sub=str(admin_user.pk),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        jti=secrets.token_hex(),
        extras={'type': 'refresh'},
    )


@pytest.fixture
def encoded_token(
    refresh_token: JWToken,
    settings: LazySettings,
) -> str:
    """Encoded refresh token of the test user."""
    return refresh_token.encode(
        secret=settings.SECRET_KEY,
        algorithm='HS256',
    )


@pytest.mark.django_db
def test_cookie_refresh_blocklisted(
    dmr_rf: DMRRequestFactory,
    refresh_token: JWToken,
    encoded_token: str,
) -> None:
    """Ensures that a blocklisted token cannot refresh the cookies."""
    request = dmr_rf.post('/whatever/')
    request.COOKIES['refresh_token'] = encoded_token
    view = _CookieRefreshSyncController.as_view()

    allowed = view(request)
    _CookieRefreshSyncController().blocklist(refresh_token)
    blocked = view(request)

    assert isinstance(allowed, HttpResponse)
    assert allowed.status_code == HTTPStatus.NO_CONTENT, allowed.content
    assert isinstance(blocked, HttpResponse)
    assert blocked.status_code == HTTPStatus.UNAUTHORIZED, blocked.content
    assert not blocked.cookies


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_refresh_blocklisted(
    dmr_async_rf: DMRAsyncRequestFactory,
    refresh_token: JWToken,
    encoded_token: str,
) -> None:
    """Ensures that a blocklisted token cannot refresh the cookies, async."""
    request = dmr_async_rf.post('/whatever/')
    request.COOKIES['refresh_token'] = encoded_token
    view = _CookieRefreshAsyncController.as_view()

    allowed = await dmr_async_rf.wrap(view(request))
    await _CookieRefreshAsyncController().blocklist(refresh_token)
    blocked = await dmr_async_rf.wrap(view(request))

    assert isinstance(allowed, HttpResponse)
    assert allowed.status_code == HTTPStatus.NO_CONTENT, allowed.content
    assert isinstance(blocked, HttpResponse)
    assert blocked.status_code == HTTPStatus.UNAUTHORIZED, blocked.content
    assert not blocked.cookies


@pytest.mark.django_db
def test_body_refresh_blocklisted(
    dmr_rf: DMRRequestFactory,
    refresh_token: JWToken,
    encoded_token: str,
) -> None:
    """Ensures that a blocklisted token cannot refresh the body tokens."""
    request = dmr_rf.post('/whatever/', {'refresh_token': encoded_token})
    view = _BodyRefreshSyncController.as_view()

    allowed = view(request)
    _BodyRefreshSyncController().blocklist(refresh_token)
    blocked = view(dmr_rf.post('/whatever/', {'refresh_token': encoded_token}))

    assert isinstance(allowed, HttpResponse)
    assert allowed.status_code == HTTPStatus.OK, allowed.content
    assert isinstance(blocked, HttpResponse)
    assert blocked.status_code == HTTPStatus.UNAUTHORIZED, blocked.content


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_body_refresh_blocklisted(
    dmr_async_rf: DMRAsyncRequestFactory,
    refresh_token: JWToken,
    encoded_token: str,
) -> None:
    """Ensures that a blocklisted token cannot refresh the tokens, async."""
    view = _BodyRefreshAsyncController.as_view()

    allowed = await dmr_async_rf.wrap(
        view(dmr_async_rf.post('/whatever/', {'refresh_token': encoded_token})),
    )
    await _BodyRefreshAsyncController().blocklist(refresh_token)
    blocked = await dmr_async_rf.wrap(
        view(dmr_async_rf.post('/whatever/', {'refresh_token': encoded_token})),
    )

    assert isinstance(allowed, HttpResponse)
    assert allowed.status_code == HTTPStatus.OK, allowed.content
    assert isinstance(blocked, HttpResponse)
    assert blocked.status_code == HTTPStatus.UNAUTHORIZED, blocked.content


@pytest.mark.django_db
def test_cookie_refresh_without_jti(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures that a token that can never be blocklisted is rejected."""
    request = dmr_rf.post('/whatever/')
    request.COOKIES['refresh_token'] = JWToken(
        sub=str(admin_user.pk),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        jti=None,
        extras={'type': 'refresh'},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    response = _CookieRefreshSyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
