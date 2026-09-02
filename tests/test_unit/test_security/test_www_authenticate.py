import json
from http import HTTPStatus
from typing import Self, TypeAlias, final

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Controller, modify
from dmr.endpoint import Endpoint
from dmr.exceptions import NotAuthenticatedError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import AsyncAuth, SyncAuth
from dmr.security.allauth import XSessionTokenAsyncAuth, XSessionTokenSyncAuth
from dmr.security.base import (
    _combined_www_authenticate,  # pyright: ignore[reportPrivateUsage]
)
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
    DjangoSessionSyncAuth,
)
from dmr.security.http import (
    HttpBasicSyncAuth,
    _quote_auth_param,  # pyright: ignore[reportPrivateUsage]
    basic_auth,
)
from dmr.security.jwt import (
    CookieJWTAsyncAuth,
    CookieJWTSyncAuth,
    HeaderJWTAsyncAuth,
    HeaderJWTSyncAuth,
)
from dmr.security.token import (
    CookieTokenAsyncAuth,
    CookieTokenSyncAuth,
    HeaderTokenAsyncAuth,
    HeaderTokenSyncAuth,
)
from dmr.serializer import BaseSerializer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory

_AuthFactory: TypeAlias = type[SyncAuth] | type[AsyncAuth]

_BASIC_CHALLENGE = 'Basic realm="api", charset="UTF-8"'


class _RejectingBasicAuth(HttpBasicSyncAuth):
    """Never lets anybody in, so we always look at the ``401``."""

    __slots__ = ()

    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        raise NotAuthenticatedError


class _AllowingAuth(HeaderJWTSyncAuth):
    """Always lets everybody in, so we can reach the endpoint body."""

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self | None:
        return self


class _CustomChallengeAuth(HeaderJWTSyncAuth):
    """Sends a challenge of its own instead of the default one."""

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self | None:
        raise NotAuthenticatedError(headers={'WWW-Authenticate': 'Custom'})


@pytest.mark.parametrize(
    ('typ', 'expected'),
    [
        # Reads the `Authorization` header, so it has a challenge to send:
        (HttpBasicSyncAuth, _BASIC_CHALLENGE),
        (HeaderJWTSyncAuth, 'Bearer'),
        (HeaderJWTAsyncAuth, 'Bearer'),
        # Reads a cookie or a custom header, so it has nothing to send:
        (CookieJWTSyncAuth, None),
        (CookieJWTAsyncAuth, None),
        (CookieTokenSyncAuth, None),
        (CookieTokenAsyncAuth, None),
        (DjangoSessionSyncAuth, None),
        (DjangoSessionAsyncAuth, None),
        (XSessionTokenSyncAuth, None),
        (XSessionTokenAsyncAuth, None),
        # Defaults to `X-API-Token` with no prefix:
        (HeaderTokenSyncAuth, None),
        (HeaderTokenAsyncAuth, None),
    ],
)
def test_default_challenges(
    *,
    typ: _AuthFactory,
    expected: str | None,
) -> None:
    """Ensures that each auth advertises the right default challenge."""
    assert typ().www_authenticate_challenge == expected


@pytest.mark.parametrize(
    ('auth', 'expected'),
    [
        (_RejectingBasicAuth(realm='my api'), 'Basic realm="my api"'),
        (_RejectingBasicAuth(realm='say "hi"'), r'Basic realm="say \"hi\""'),
        # A custom header cannot be asked for in a challenge:
        (_RejectingBasicAuth(header='X-Auth'), None),
        (_RejectingBasicAuth(www_authenticate=False), None),
        (HeaderJWTSyncAuth(auth_scheme='JWT'), 'JWT'),
        (HeaderJWTSyncAuth(auth_header='X-Api-Auth'), None),
        (HeaderJWTSyncAuth(www_authenticate=False), None),
        (
            HeaderTokenSyncAuth(header_name='Authorization', prefix='Token'),
            'Token',
        ),
        # Without a prefix there is no scheme name to build a challenge from:
        (HeaderTokenSyncAuth(header_name='Authorization'), None),
        (
            HeaderTokenSyncAuth(
                header_name='Authorization',
                prefix='Token',
                www_authenticate=False,
            ),
            None,
        ),
        # Async token auth repeats the whole `__init__`, so check it as well:
        (
            HeaderTokenAsyncAuth(header_name='Authorization', prefix='Token'),
            'Token',
        ),
        (HeaderTokenAsyncAuth(header_name='Authorization'), None),
        (
            HeaderTokenAsyncAuth(
                header_name='Authorization',
                prefix='Token',
                www_authenticate=False,
            ),
            None,
        ),
    ],
)
def test_customized_challenges(
    *,
    auth: SyncAuth | AsyncAuth,
    expected: str | None,
) -> None:
    """Ensures that auth configuration changes the challenge."""
    challenge = auth.www_authenticate_challenge
    if expected is None:
        assert challenge is None
    else:
        # `charset` is only added by http basic auth:
        assert challenge is not None
        assert challenge.startswith(expected)


@pytest.mark.parametrize(
    ('auth', 'expected'),
    [
        (None, None),
        ([], None),
        ([CookieJWTSyncAuth()], None),
        ([HeaderJWTSyncAuth()], 'Bearer'),
        ([CookieJWTSyncAuth(), _RejectingBasicAuth()], _BASIC_CHALLENGE),
        (
            [_RejectingBasicAuth(), HeaderJWTSyncAuth()],
            f'{_BASIC_CHALLENGE}, Bearer',
        ),
        # Duplicates are reported just once:
        (
            [HeaderJWTSyncAuth(), HeaderJWTSyncAuth(security_scheme_name='2')],
            'Bearer',
        ),
    ],
)
def test_combined_www_authenticate(
    *,
    auth: list[SyncAuth] | None,
    expected: str | None,
) -> None:
    """Ensures that all challenges of an auth chain are joined together."""
    assert _combined_www_authenticate(auth) == expected


def test_quote_auth_param() -> None:
    """Ensures that auth params are escaped as `quoted-string`."""
    assert _quote_auth_param('api') == '"api"'
    assert _quote_auth_param(r'back\slash') == r'"back\\slash"'


def test_unauthed_response_has_challenge(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that a `401` advertises how to authenticate."""

    @final
    class _Controller(Controller[PydanticSerializer]):
        @modify(auth=[_RejectingBasicAuth()])
        def get(self) -> str:
            raise NotImplementedError

    request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': basic_auth('test', 'wrong')},
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers['WWW-Authenticate'] == _BASIC_CHALLENGE


def test_challenge_for_hand_raised_error(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that a `401` raised from the endpoint body is also covered."""

    @final
    class _Controller(Controller[PydanticSerializer]):
        # This auth succeeds, so we do reach the endpoint body:
        @modify(auth=[_AllowingAuth()])
        def get(self) -> str:
            raise NotAuthenticatedError

    request = dmr_rf.get('/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers['WWW-Authenticate'] == 'Bearer'


def test_explicit_headers_win(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that we don't overwrite headers that an auth has passed."""

    @final
    class _Controller(Controller[PydanticSerializer]):
        @modify(auth=[_CustomChallengeAuth()])
        def get(self) -> str:
            raise NotImplementedError

    request = dmr_rf.get('/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers['WWW-Authenticate'] == 'Custom'


def test_no_challenge_for_cookie_auth(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures that cookie auth sends no challenge it cannot express."""
    settings.DMR_SETTINGS = {Settings.auth: [CookieJWTSyncAuth()]}

    @final
    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    request = dmr_rf.get('/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.parametrize(
    ('auth', 'documented'),
    [
        (HeaderJWTSyncAuth(), True),
        (CookieJWTSyncAuth(), False),
        (HeaderJWTSyncAuth(www_authenticate=False), False),
        # The cookie auth builds the `401` spec, the basic one has a challenge:
        ([CookieJWTSyncAuth(), _RejectingBasicAuth()], True),
    ],
)
def test_challenge_in_openapi(
    *,
    auth: SyncAuth | list[SyncAuth],
    documented: bool,
) -> None:
    """Ensures that the header is only documented when we can send it."""
    auth_chain = auth if isinstance(auth, list) else [auth]

    @final
    class _Controller(Controller[PydanticSerializer]):
        @modify(auth=auth_chain)
        def get(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    unauthed = metadata.responses[HTTPStatus.UNAUTHORIZED]

    assert bool(unauthed.headers) is documented
