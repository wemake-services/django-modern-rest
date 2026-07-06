import json
from http import HTTPStatus
from typing import final

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.token import CookieTokenAsyncAuth, CookieTokenSyncAuth
from dmr.security.token.logic import token_acreate, token_create
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@pytest.mark.django_db
def test_cookie_token_sync_auth_success(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures CookieTokenSyncAuth reads the token from a cookie."""

    @final
    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def get(self) -> str:
            return 'authed'

    _, raw_token = token_create(
        user=admin_user,
        name='cookie-test',
    )
    request = dmr_rf.get('/whatever/')
    request.COOKIES['token'] = raw_token

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_cookie_token_sync_auth_missing_cookie(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures CookieTokenSyncAuth returns 401 when the cookie is absent."""

    @final
    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def get(self) -> str:  # pragma: no cover
            return 'authed'

    request = dmr_rf.get('/whatever/')

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_token_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
) -> None:
    """Ensures CookieTokenAsyncAuth reads the token from a cookie."""

    @final
    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def get(self) -> str:
            return 'authed'

    _, raw_token = await token_acreate(
        user=admin_user,
        name='async-cookie-test',
    )
    request = dmr_async_rf.get('/whatever/')
    request.COOKIES['token'] = raw_token

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_cookie_token_auth_missing_cookie(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures CookieTokenAsyncAuth returns 401 when the cookie is absent."""

    @final
    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def get(self) -> str:  # pragma: no cover
            return 'authed'

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_sync_cookie_token_auth_csrf_enforced(
    admin_user: User,
) -> None:
    """Ensures CookieTokenSyncAuth rejects POST without a CSRF token."""

    @final
    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def post(self) -> str:  # pragma: no cover
            # CSRF validation happens during auth, before route execution.
            # This method should never be reached on CSRF-invalid requests.
            return 'authed'

    _, raw_token = token_create(
        user=admin_user,
        name='cookie-csrf-test',
    )
    csrf_rf = DMRRequestFactory()
    request = csrf_rf.post('/whatever/')
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
) -> None:
    """Ensures CookieTokenAsyncAuth rejects POST without a CSRF token."""

    @final
    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def post(self) -> str:  # pragma: no cover
            # CSRF validation happens during auth, before route execution.
            # This method should never be reached on CSRF-invalid requests.
            return 'authed'

    _, raw_token = await token_acreate(
        user=admin_user,
        name='async-cookie-csrf-test',
    )
    csrf_async_rf = DMRAsyncRequestFactory()
    request = csrf_async_rf.post('/whatever/')
    request.COOKIES['token'] = raw_token
    assert settings.CSRF_COOKIE_NAME not in request.COOKIES

    response = await csrf_async_rf.wrap(
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures CookieTokenSyncAuth succeeds when CSRF passes."""

    @final
    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenSyncAuth(),)

        def post(self) -> str:
            return 'authed'

    _, raw_token = token_create(
        user=admin_user,
        name='cookie-csrf-valid-test',
    )

    monkeypatch.setattr(
        'dmr.security._csrf._get_csrf_failure_reason',
        lambda _: None,
    )

    request = dmr_rf.post('/whatever/')
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures CookieTokenAsyncAuth succeeds when CSRF passes."""

    @final
    class _AsyncCookieController(Controller[PydanticFastSerializer]):
        auth = (CookieTokenAsyncAuth(),)

        async def post(self) -> str:
            return 'authed'

    _, raw_token = await token_acreate(
        user=admin_user,
        name='async-cookie-csrf-valid-test',
    )

    monkeypatch.setattr(
        'dmr.security._csrf._get_csrf_failure_reason',
        lambda _: None,
    )

    request = dmr_async_rf.post('/whatever/')
    request.COOKIES['token'] = raw_token

    response = await dmr_async_rf.wrap(
        _AsyncCookieController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == 'authed'
