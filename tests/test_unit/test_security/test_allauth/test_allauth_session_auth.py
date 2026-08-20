import json
from collections.abc import Callable
from http import HTTPStatus
from importlib import import_module

import pytest
from django.conf import LazySettings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.http import HttpResponse

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import request_auth
from dmr.security.allauth import (
    XSessionTokenAsyncAuth,
    XSessionTokenSyncAuth,
    request_allauth_session,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@pytest.fixture
def make_session_token(
    settings: LazySettings,
) -> Callable[[User], str]:
    """Create an allauth-compatible session token for a user."""

    def factory(user: User) -> str:
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore()
        # This is what `django-allauth` looks up the user by:
        session[SESSION_KEY] = str(user.pk)
        session.save()
        # The default `SessionTokenStrategy` uses the session key as a token:
        token = session.session_key
        assert isinstance(token, str)
        return token

    return factory


@pytest.fixture
def session_token(
    make_session_token: Callable[[User], str],
    admin_user: User,
) -> str:
    """
    Session token for the admin user.

    Async tests must use this instead of calling the factory themselves:
    fixtures are resolved outside the coroutine, so the sync session
    store access here does not raise ``SynchronousOnlyOperation``.
    """
    return make_session_token(admin_user)


class _SyncController(Controller[PydanticFastSerializer]):
    auth = (XSessionTokenSyncAuth(),)

    def get(self) -> str:
        assert self.request.user.is_authenticated
        assert request_allauth_session(self.request, strict=True)
        return 'authed'


class _AsyncController(Controller[PydanticFastSerializer]):
    auth = (XSessionTokenAsyncAuth(),)

    async def get(self) -> str:
        auser = await self.request.auser()
        assert auser.is_authenticated
        assert request_allauth_session(self.request, strict=True)
        return 'authed'


@pytest.mark.django_db
def test_sync_session_token_auth(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    make_session_token: Callable[[User], str],
) -> None:
    """Ensures XSessionTokenSyncAuth authenticates a valid token."""
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-Session-Token': make_session_token(admin_user)},
    )

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'
    assert isinstance(request_auth(request), XSessionTokenSyncAuth)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_async_session_token_auth(
    dmr_async_rf: DMRAsyncRequestFactory,
    session_token: str,
) -> None:
    """Ensures XSessionTokenAsyncAuth authenticates a valid token."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'X-Session-Token': session_token},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
@pytest.mark.parametrize(
    'headers',
    [
        {},
        {'X-Session-Token': ''},
        {'X-Session-Token': 'not-a-real-session-key'},
        {'Wrong-Header': 'whatever'},
    ],
)
def test_sync_session_token_auth_rejected(
    dmr_rf: DMRRequestFactory,
    *,
    headers: dict[str, str],
) -> None:
    """Ensures missing and unknown tokens are not authenticated."""
    request = dmr_rf.get('/whatever/', headers=headers)

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    'headers',
    [
        {},
        {'X-Session-Token': ''},
        {'X-Session-Token': 'not-a-real-session-key'},
        {'Wrong-Header': 'whatever'},
    ],
)
async def test_async_session_token_auth_rejected(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    headers: dict[str, str],
) -> None:
    """Ensures missing and unknown tokens are not authenticated."""
    request = dmr_async_rf.get('/whatever/', headers=headers)

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_sync_session_token_inactive_user(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    make_session_token: Callable[[User], str],
) -> None:
    """Ensures that sessions of deactivated users stop working."""
    token = make_session_token(admin_user)
    admin_user.is_active = False
    admin_user.save()

    request = dmr_rf.get('/whatever/', headers={'X-Session-Token': token})

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_sync_session_token_custom_header(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    make_session_token: Callable[[User], str],
) -> None:
    """Ensures that the token header name is customizable."""

    class _CustomController(Controller[PydanticFastSerializer]):
        auth = (XSessionTokenSyncAuth(header_name='X-Auth'),)

        def get(self) -> str:
            return 'authed'

    request = dmr_rf.get(
        '/whatever/',
        headers={'X-Auth': make_session_token(admin_user)},
    )

    response = _CustomController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
def test_session_token_auth_falls_through(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    make_session_token: Callable[[User], str],
) -> None:
    """Ensures a missing token does not block the next auth in the chain."""

    class _ChainedController(Controller[PydanticFastSerializer]):
        auth = (
            XSessionTokenSyncAuth(),
            XSessionTokenSyncAuth(header_name='X-Other-Token'),
        )

        def get(self) -> str:
            return 'authed'

    # Only the second auth's header is present:
    request = dmr_rf.get(
        '/whatever/',
        headers={'X-Other-Token': make_session_token(admin_user)},
    )

    response = _ChainedController.as_view()(request)

    # The first auth returned `None` instead of failing the request,
    # which let the second one run and authenticate:
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
def test_request_allauth_session_absent(dmr_rf: DMRRequestFactory) -> None:
    """Ensures the session accessor behaves without any auth."""
    request = dmr_rf.get('/whatever/')

    assert request_allauth_session(request) is None
    with pytest.raises(AttributeError):
        request_allauth_session(request, strict=True)
