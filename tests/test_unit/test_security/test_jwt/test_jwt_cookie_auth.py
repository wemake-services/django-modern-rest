import datetime as dt
import json
from collections.abc import Callable
from http import HTTPStatus

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.openapi.objects import SecurityScheme
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import request_auth
from dmr.security.jwt import (
    CookieJWTAsyncAuth,
    CookieJWTSyncAuth,
    JWToken,
    JWTSyncAuth,
    request_jwt,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


def _encode(user: User, secret: str) -> str:
    return JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=str(user.pk),
    ).encode(secret=secret, algorithm='HS256')


@pytest.mark.parametrize('typ', [CookieJWTSyncAuth, CookieJWTAsyncAuth])
def test_cookie_jwt_schema(
    *,
    typ: type[CookieJWTSyncAuth] | type[CookieJWTAsyncAuth],
) -> None:
    """Ensures that security scheme is correct for cookie jwt auth."""
    instance = typ()

    assert instance.security_schemes == snapshot({
        'jwt': SecurityScheme(
            type='apiKey',
            description='JWT token auth via cookie',
            name='access_token',
            security_scheme_in='cookie',
        ),
    })
    assert instance.security_requirement == snapshot({'jwt': []})


@pytest.mark.parametrize('typ', [CookieJWTSyncAuth, CookieJWTAsyncAuth])
def test_cookie_jwt_custom_schema(
    *,
    typ: type[CookieJWTSyncAuth] | type[CookieJWTAsyncAuth],
) -> None:
    """Ensures that cookie and scheme names are customizable."""
    instance = typ(cookie_name='my-jwt', security_scheme_name='my-scheme')

    assert instance.security_schemes == snapshot({
        'my-scheme': SecurityScheme(
            type='apiKey',
            description='JWT token auth via cookie',
            name='my-jwt',
            security_scheme_in='cookie',
        ),
    })
    assert instance.security_requirement == snapshot({'my-scheme': []})


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('cookie_name', 'cookie_value', 'expected_status'),
    [
        ('access_token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('access_token', 'Bearer {0}', HTTPStatus.UNAUTHORIZED),
        ('access_token', '', HTTPStatus.UNAUTHORIZED),
        ('wrong', '{0}', HTTPStatus.UNAUTHORIZED),
        ('access_token', '{0}', HTTPStatus.OK),
    ],
)
def test_sync_cookie_jwt_auth(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
    *,
    cookie_name: str,
    cookie_value: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures CookieJWTSyncAuth reads the token from a cookie."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(),)

        def get(self) -> str:
            assert request_jwt(self.request)
            return 'authed'

    token = _encode(admin_user, settings.SECRET_KEY)
    request = dmr_rf.get('/whatever/')
    request.COOKIES[cookie_name] = cookie_value.format(token)

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status
    if expected_status == HTTPStatus.OK:
        assert isinstance(request_auth(request), CookieJWTSyncAuth)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('cookie_name', 'cookie_value', 'expected_status'),
    [
        ('access_token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('access_token', 'Bearer {0}', HTTPStatus.UNAUTHORIZED),
        ('access_token', '', HTTPStatus.UNAUTHORIZED),
        ('wrong', '{0}', HTTPStatus.UNAUTHORIZED),
        ('access_token', '{0}', HTTPStatus.OK),
    ],
)
async def test_async_cookie_jwt_auth(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    settings: LazySettings,
    *,
    cookie_name: str,
    cookie_value: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures CookieJWTAsyncAuth reads the token from a cookie."""

    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTAsyncAuth(),)

        async def get(self) -> str:
            assert request_jwt(self.request)
            return 'authed'

    token = _encode(admin_user, settings.SECRET_KEY)
    request = dmr_async_rf.get('/whatever/')
    request.COOKIES[cookie_name] = cookie_value.format(token)

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status


@pytest.mark.django_db
def test_sync_cookie_jwt_auth_csrf_enforced(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures CookieJWTSyncAuth rejects POST without a CSRF token."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(),)

        def post(self) -> str:
            # CSRF validation happens during auth, before route execution.
            # This method should never be reached on CSRF-invalid requests.
            raise NotImplementedError

    token = _encode(admin_user, settings.SECRET_KEY)
    request = dmr_rf.post('/whatever/')
    request.COOKIES['access_token'] = token
    assert settings.CSRF_COOKIE_NAME not in request.COOKIES

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'CSRF Failed: CSRF cookie not set.',
            },
        ],
    })


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_jwt_auth_csrf_enforced(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures CookieJWTAsyncAuth rejects POST without a CSRF token."""

    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTAsyncAuth(),)

        async def post(self) -> str:
            # CSRF validation happens during auth, before route execution.
            # This method should never be reached on CSRF-invalid requests.
            raise NotImplementedError

    token = _encode(admin_user, settings.SECRET_KEY)
    request = dmr_async_rf.post('/whatever/')
    request.COOKIES['access_token'] = token
    assert settings.CSRF_COOKIE_NAME not in request.COOKIES

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'CSRF Failed: CSRF cookie not set.',
            },
        ],
    })


@pytest.mark.django_db
def test_sync_cookie_jwt_auth_with_valid_csrf(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
    fill_csrf: Callable[[HttpRequest], HttpRequest],
) -> None:
    """Ensures CookieJWTSyncAuth succeeds when CSRF passes."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(),)

        def post(self) -> str:
            return 'authed'

    token = _encode(admin_user, settings.SECRET_KEY)
    request = dmr_rf.post('/whatever/')
    fill_csrf(request)
    request.COOKIES['access_token'] = token

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == 'authed'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_jwt_auth_with_valid_csrf(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    settings: LazySettings,
    fill_csrf: Callable[[HttpRequest], HttpRequest],
) -> None:
    """Ensures CookieJWTAsyncAuth succeeds when CSRF passes."""

    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTAsyncAuth(),)

        async def post(self) -> str:
            return 'authed'

    token = _encode(admin_user, settings.SECRET_KEY)
    request = dmr_async_rf.post('/whatever/')
    fill_csrf(request)
    request.COOKIES['access_token'] = token

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
def test_sync_cookie_jwt_falls_to_header(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures a missing cookie does not block the next auth in the chain."""

    class _ChainedController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(), JWTSyncAuth())

        def post(self) -> str:
            return 'authed'

    token = _encode(admin_user, settings.SECRET_KEY)
    request = dmr_rf.post(
        '/whatever/',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert settings.CSRF_COOKIE_NAME not in request.COOKIES

    response = _ChainedController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert isinstance(request_auth(request), JWTSyncAuth)
    assert json.loads(response.content) == 'authed'
