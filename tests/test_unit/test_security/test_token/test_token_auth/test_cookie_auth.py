import datetime as dt
import json
from collections.abc import Callable
from http import HTTPStatus
from typing import Final

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token import CookieTokenAsyncAuth, CookieTokenSyncAuth
from dmr.security.token.app.models import Token
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_CORRECT_TEMPLATE: Final = '{0}'


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('cookie_name', 'cookie_value', 'expected_status'),
    [
        ('token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('token', 'Prefix {0}', HTTPStatus.UNAUTHORIZED),
        ('wrong', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('token', _CORRECT_TEMPLATE, HTTPStatus.OK),
    ],
)
def test_cookie_token_sync_auth(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    *,
    cookie_name: str,
    cookie_value: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures CookieTokenSyncAuth reads the token from a cookie."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='cookie-test',
    )
    request = dmr_rf.get('/whatever/')
    request.COOKIES[cookie_name] = cookie_value.format(raw_token)

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('cookie_name', 'cookie_value', 'expected_status'),
    [
        ('token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('token', 'Prefix {0}', HTTPStatus.UNAUTHORIZED),
        ('wrong', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('token', _CORRECT_TEMPLATE, HTTPStatus.OK),
    ],
)
async def test_async_cookie_token_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    *,
    cookie_name: str,
    cookie_value: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures CookieTokenAsyncAuth reads the token from a cookie."""

    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-cookie-test',
    )
    request = dmr_async_rf.get('/whatever/')
    request.COOKIES[cookie_name] = cookie_value.format(raw_token)

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status


@pytest.mark.django_db
def test_sync_cookie_token_auth_csrf_enforced(
    admin_user: User,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures CookieTokenSyncAuth rejects POST without a CSRF token."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def post(self) -> str:
            # CSRF validation happens during auth, before route execution.
            # This method should never be reached on CSRF-invalid requests.
            raise NotImplementedError

    _, raw_token = Token.issue(
        user=admin_user,
        name='cookie-csrf-test',
    )
    request = dmr_rf.post('/whatever/')
    request.COOKIES['token'] = raw_token
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
async def test_async_cookie_token_auth_csrf_enforced(
    admin_user: User,
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures CookieTokenAsyncAuth rejects POST without a CSRF token."""

    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def post(self) -> str:
            # CSRF validation happens during auth, before route execution.
            # This method should never be reached on CSRF-invalid requests.
            raise NotImplementedError

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-cookie-csrf-test',
    )
    request = dmr_async_rf.post('/whatever/')
    request.COOKIES['token'] = raw_token
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
def test_sync_cookie_token_auth_with_valid_csrf(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    fill_csrf: Callable[[HttpRequest], HttpRequest],
) -> None:
    """Ensures CookieTokenSyncAuth succeeds when CSRF passes."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def post(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='cookie-csrf-valid-test',
    )

    request = dmr_rf.post('/whatever/')
    fill_csrf(request)
    request.COOKIES['token'] = raw_token

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == 'authed'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_token_auth_with_valid_csrf(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    fill_csrf: Callable[[HttpRequest], HttpRequest],
) -> None:
    """Ensures CookieTokenAsyncAuth succeeds when CSRF passes."""

    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def post(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-cookie-csrf-valid-test',
    )

    request = dmr_async_rf.post('/whatever/')
    fill_csrf(request)
    request.COOKIES['token'] = raw_token

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
def test_sync_cookie_token_auth_update_last_used(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures update_last_used=True sets last_used_at on successful cookie auth (sync)."""

    class _UpdateController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(update_last_used=True),)

        def get(self) -> str:
            return 'authed'

    token, raw_token = Token.issue(user=admin_user, name='cookie-update-used')
    request = dmr_rf.get('/whatever/')
    request.COOKIES['token'] = raw_token

    response = _UpdateController.as_view()(request)

    token.refresh_from_db()
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(token.last_used_at, dt.datetime)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_token_auth_update_last_used(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures update_last_used=True sets last_used_at on successful cookie auth (async)."""

    class _AsyncUpdateController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(update_last_used=True),)

        async def get(self) -> str:
            return 'authed'

    token, raw_token = await Token.aissue(user=admin_user, name='async-cookie-update-used')
    request = dmr_async_rf.get('/whatever/')
    request.COOKIES['token'] = raw_token

    response = await dmr_async_rf.wrap(_AsyncUpdateController.as_view()(request))

    await token.arefresh_from_db()
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(token.last_used_at, dt.datetime)
