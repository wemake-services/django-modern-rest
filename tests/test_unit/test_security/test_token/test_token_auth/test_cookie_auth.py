import json
from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import request_auth
from dmr.security.token import (
    CookieTokenAsyncAuth,
    CookieTokenSyncAuth,
    HeaderTokenAsyncAuth,
    HeaderTokenSyncAuth,
)
from dmr.security.token.app.models import Token
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

if TYPE_CHECKING:
    from tests.test_unit.conftest import CsrfFailureAssertion

_CORRECT_TEMPLATE: Final = '{0}'


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('cookie_name', 'cookie_value', 'expected_status'),
    [
        ('token', 'not-a-token', HTTPStatus.UNAUTHORIZED),
        ('token', 'Prefix {0}', HTTPStatus.UNAUTHORIZED),
        ('token', 'Bearer {0}', HTTPStatus.UNAUTHORIZED),
        ('wrong', _CORRECT_TEMPLATE, HTTPStatus.UNAUTHORIZED),
        ('token', _CORRECT_TEMPLATE, HTTPStatus.OK),
    ],
)
def test_cookie_token_sync_auth_safe(
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


def test_cookie_token_sync_auth_unsafe(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    fill_csrf: Callable[[HttpRequest], HttpRequest],
    assert_csrf_failure_message: 'CsrfFailureAssertion',
) -> None:
    """Ensures CookieTokenSyncAuth reads the token from a cookie."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def post(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='cookie-test',
    )
    request = dmr_rf.post('/whatever/')
    request.COOKIES['token'] = raw_token
    fill_csrf(request)

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == 'authed'

    request = dmr_rf.post('/whatever/')
    request.COOKIES['token'] = raw_token

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert_csrf_failure_message(response)


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


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_token_auth_unsafe(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    fill_csrf: Callable[[HttpRequest], HttpRequest],
    assert_csrf_failure_message: 'CsrfFailureAssertion',
) -> None:
    """Ensures CookieTokenAsyncAuth reads the token from a cookie."""

    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def post(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-cookie-test',
    )
    request = dmr_async_rf.post('/whatever/')
    request.COOKIES['token'] = raw_token
    fill_csrf(request)

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == 'authed'

    request = dmr_async_rf.post('/whatever/')
    request.COOKIES['token'] = raw_token

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert_csrf_failure_message(response)


@pytest.mark.django_db
def test_cookie_auth_try_next_sync(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures you can try next auth after cookie auth."""

    class _SyncController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(), HeaderTokenSyncAuth())

        def post(self) -> str:
            return 'authed'

    _, raw_token = Token.issue(
        user=admin_user,
        name='test',
    )
    request = dmr_rf.post(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )
    request.COOKIES = {}

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert isinstance(request_auth(request), HeaderTokenSyncAuth)
    assert json.loads(response.content) == 'authed'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_cookie_auth_try_next_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures async controllers work with token auth."""

    class _AsyncController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(), HeaderTokenAsyncAuth())

        async def post(self) -> str:
            return 'authed'

    _, raw_token = await Token.aissue(
        user=admin_user,
        name='async-test',
    )
    request = dmr_async_rf.post(
        '/whatever/',
        headers={'X-API-Token': raw_token},
    )
    assert settings.CSRF_COOKIE_NAME not in request.COOKIES

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert isinstance(request_auth(request), HeaderTokenAsyncAuth)
    assert json.loads(response.content) == 'authed'
