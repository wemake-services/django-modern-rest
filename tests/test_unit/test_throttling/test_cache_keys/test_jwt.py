import datetime as dt
import hashlib
import json
from http import HTTPStatus
from typing import Final

import pytest
from django.http import HttpResponse
from freezegun.api import FrozenDateTimeFactory

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import JWToken
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.throttling import AsyncThrottle, Rate, SyncThrottle
from dmr.throttling.cache_keys import JwtToken


class _SyncController(Controller[PydanticSerializer]):
    throttling = [
        SyncThrottle(1, Rate.second, cache_key=JwtToken()),
    ]

    def get(self) -> str:
        return 'inside'


class _AsyncController(Controller[PydanticSerializer]):
    throttling = [
        AsyncThrottle(1, Rate.second, cache_key=JwtToken()),
    ]

    async def get(self) -> str:
        return 'inside'


_JWT_THROTTLE_CASES: Final = (
    (
        True,
        JWToken(
            sub='1',
            exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            jti='jwt-1',
        ),
        HTTPStatus.TOO_MANY_REQUESTS,
    ),
    (True, None, HTTPStatus.OK),
    (False, None, HTTPStatus.OK),
)


@pytest.mark.parametrize(
    ('set_jwt', 'jwt_value', 'expected_second'),
    _JWT_THROTTLE_CASES,
)
def test_sync_throttle_jwt_token_cases(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    set_jwt: bool,
    jwt_value: JWToken | None,
    expected_second: HTTPStatus,
) -> None:
    """Ensures `JwtToken` cache key behavior for jwt/no-jwt requests."""
    request = dmr_rf.get('/whatever/')
    if set_jwt:
        request.__dmr_jwt__ = jwt_value  # type: ignore[attr-defined]
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == 'inside'

    request = dmr_rf.get('/whatever/')
    if set_jwt:
        request.__dmr_jwt__ = jwt_value  # type: ignore[attr-defined]
    response = _SyncController.as_view()(request)
    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_second


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('set_jwt', 'jwt_value', 'expected_second'),
    _JWT_THROTTLE_CASES,
)
async def test_async_throttle_jwt_token_cases(
    dmr_async_rf: DMRAsyncRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    set_jwt: bool,
    jwt_value: JWToken | None,
    expected_second: HTTPStatus,
) -> None:
    """Ensures `JwtToken` cache key behavior in async controllers."""
    request = dmr_async_rf.get('/whatever/')
    if set_jwt:
        request.__dmr_jwt__ = jwt_value  # type: ignore[attr-defined]
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == 'inside'

    request = dmr_async_rf.get('/whatever/')
    if set_jwt:
        request.__dmr_jwt__ = jwt_value  # type: ignore[attr-defined]
    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))
    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_second


@pytest.mark.parametrize(
    'token',
    [
        JWToken(
            sub='1',
            exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            jti='jwt-1',
        ),
        JWToken(
            sub='user@example.com',
            exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        ),
    ],
)
def test_jwt_cache_key_is_hashed(
    dmr_rf: DMRRequestFactory,
    freezer: FrozenDateTimeFactory,
    *,
    token: JWToken,
) -> None:
    """Ensures `JwtToken` never exposes raw token data in cache key."""
    raw_value = token.sub if token.jti is None else token.jti
    endpoint = _SyncController.api_endpoints['GET']
    controller = _SyncController()
    request = dmr_rf.get('/whatever/')
    request.__dmr_jwt__ = token  # type: ignore[attr-defined]
    controller.request = request

    cache_key = JwtToken()(endpoint, controller)

    assert cache_key == hashlib.sha256(raw_value.encode('utf-8')).hexdigest()
    assert cache_key != raw_value
    assert cache_key != str(token)


def test_jwt_cache_key_is_none(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures `JwtToken` returns `None` when both claims are missing."""

    class _TokenWithoutClaims:
        jti = None
        sub = None

    endpoint = _SyncController.api_endpoints['GET']
    controller = _SyncController()
    request = dmr_rf.get('/whatever/')
    request.__dmr_jwt__ = _TokenWithoutClaims()  # type: ignore[attr-defined]
    controller.request = request

    assert JwtToken()(endpoint, controller) is None
