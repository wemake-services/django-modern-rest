import datetime as dt
import json
from collections.abc import Callable
from http import HTTPStatus
from typing import Final

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from freezegun.api import FrozenDateTimeFactory
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Controller
from dmr.openapi.objects import SecurityScheme
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import request_auth
from dmr.security.jwt import (
    BaseJWTSyncAuth,
    CookieJWTAsyncAuth,
    CookieJWTSyncAuth,
    HeaderJWTAsyncAuth,
    HeaderJWTSyncAuth,
    JWToken,
    request_jwt,
)
from dmr.security.jwt.auth.header import JWTAsyncAuth, JWTSyncAuth
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

_LEEWAY: Final = 30  # seconds


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

    assert instance.security_schemes == snapshot(
        {
            'jwt': SecurityScheme(
                type='apiKey',
                description='JWT token auth via cookie',
                name='access_token',
                security_scheme_in='cookie',
            ),
        },
    )
    assert instance.security_requirement == snapshot({'jwt': []})


@pytest.mark.parametrize('typ', [CookieJWTSyncAuth, CookieJWTAsyncAuth])
def test_cookie_jwt_custom_schema(
    *,
    typ: type[CookieJWTSyncAuth] | type[CookieJWTAsyncAuth],
) -> None:
    """Ensures that cookie and scheme names are customizable."""
    instance = typ(cookie_name='my-jwt', security_scheme_name='my-scheme')

    assert instance.security_schemes == snapshot(
        {
            'my-scheme': SecurityScheme(
                type='apiKey',
                description='JWT token auth via cookie',
                name='my-jwt',
                security_scheme_in='cookie',
            ),
        },
    )
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
    assert json.loads(response.content) == snapshot(
        {
            'detail': [
                {
                    'msg': 'CSRF Failed: CSRF cookie not set.',
                },
            ],
        },
    )


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
    assert json.loads(response.content) == snapshot(
        {
            'detail': [
                {
                    'msg': 'CSRF Failed: CSRF cookie not set.',
                },
            ],
        },
    )


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


@pytest.mark.django_db
def test_sync_cookie_jwt_custom_algorithm(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures `algorithm` is honored and mismatches are rejected."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(algorithm='HS512'),)

        def get(self) -> str:
            return 'authed'

    matching = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=str(admin_user.pk),
    ).encode(secret=settings.SECRET_KEY, algorithm='HS512')
    request = dmr_rf.get('/whatever/')
    request.COOKIES['access_token'] = matching

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content

    # A token signed with the default `HS256` must not pass:
    other = dmr_rf.get('/whatever/')
    other.COOKIES['access_token'] = _encode(admin_user, settings.SECRET_KEY)

    mismatched = _CookieController.as_view()(other)

    assert isinstance(mismatched, HttpResponse)
    assert mismatched.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
def test_sync_cookie_jwt_custom_user_id_field(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures `user_id_field` looks the user up by another field."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(user_id_field='username'),)

        def get(self) -> str:
            assert self.request.user.pk == admin_user.pk
            return 'authed'

    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=admin_user.username,
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get('/whatever/')
    request.COOKIES['access_token'] = token

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
def test_sync_cookie_jwt_custom_secret(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures `secret` is used instead of `settings.SECRET_KEY`."""
    secret = 'a-completely-different-secret-value'  # noqa: S105

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(secret=secret),)

        def get(self) -> str:
            return 'authed'

    request = dmr_rf.get('/whatever/')
    request.COOKIES['access_token'] = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=str(admin_user.pk),
    ).encode(secret=secret, algorithm='HS256')

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content

    # A token signed with `settings.SECRET_KEY` must not pass:
    other = dmr_rf.get('/whatever/')
    other.COOKIES['access_token'] = _encode(admin_user, settings.SECRET_KEY)

    mismatched = _CookieController.as_view()(other)

    assert isinstance(mismatched, HttpResponse)
    assert mismatched.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('issuer', 'expected_status'),
    [
        ('trusted-issuer', HTTPStatus.OK),
        ('someone-else', HTTPStatus.UNAUTHORIZED),
    ],
)
def test_sync_cookie_jwt_accepted_issuers(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
    *,
    issuer: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures `accepted_issuers` is validated for cookie auth."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(accepted_issuers='trusted-issuer'),)

        def get(self) -> str:
            return 'authed'

    request = dmr_rf.get('/whatever/')
    request.COOKIES['access_token'] = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=str(admin_user.pk),
        iss=issuer,
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('audience', 'expected_status'),
    [
        ('dev', HTTPStatus.OK),
        ('prod', HTTPStatus.UNAUTHORIZED),
    ],
)
def test_sync_cookie_jwt_accepted_audiences(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
    *,
    audience: str,
    expected_status: HTTPStatus,
) -> None:
    """Ensures `accepted_audiences` is validated for cookie auth."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(accepted_audiences=('dev', 'qa')),)

        def get(self) -> str:
            return 'authed'

    request = dmr_rf.get('/whatever/')
    request.COOKIES['access_token'] = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=str(admin_user.pk),
        aud=audience,
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status


@pytest.mark.django_db
def test_sync_cookie_jwt_custom_token_cls(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures `token_cls` and `claim_from_token` can be customized."""

    class _EmailToken(JWToken):
        """Carries the user email in the `extras` claim bag."""

    class _EmailCookieAuth(CookieJWTSyncAuth):
        @override
        def claim_from_token(self, token: JWToken) -> str:
            return str(token.extras['email'])

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (_EmailCookieAuth(token_cls=_EmailToken, user_id_field='email'),)

        def get(self) -> str:
            assert isinstance(request_jwt(self.request, strict=True), JWToken)
            return 'authed'

    admin_user.email = 'someone@example.com'
    admin_user.save()
    request = dmr_rf.get('/whatever/')
    request.COOKIES['access_token'] = _EmailToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        sub=str(admin_user.pk),
        extras={'email': admin_user.email},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.django_db
@pytest.mark.freeze_time('02-11-2025 10:15:00')
@pytest.mark.parametrize(
    ('elapsed', 'expected_status'),
    [
        (_LEEWAY - 1, HTTPStatus.OK),
        (_LEEWAY + 1, HTTPStatus.UNAUTHORIZED),
    ],
)
def test_sync_cookie_jwt_leeway(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
    freezer: FrozenDateTimeFactory,
    *,
    elapsed: int,
    expected_status: HTTPStatus,
) -> None:
    """Ensures `leeway` tolerates a slightly expired token."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(leeway=_LEEWAY),)

        def get(self) -> str:
            return 'authed'

    token = JWToken(
        exp=dt.datetime.now(dt.UTC),
        sub=str(admin_user.pk),
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    # Move into the future, so the token is already expired:
    freezer.tick(delta=elapsed)
    request = dmr_rf.get('/whatever/')
    request.COOKIES['access_token'] = token

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status


@pytest.mark.django_db
def test_sync_cookie_jwt_inactive_user(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
    settings: LazySettings,
) -> None:
    """Ensures deactivated users are rejected by cookie auth."""

    class _CookieController(Controller[PydanticFastSerializer]):
        auth = (CookieJWTSyncAuth(),)

        def get(self) -> str:
            raise NotImplementedError

    admin_user.is_active = False
    admin_user.save()
    request = dmr_rf.get('/whatever/')
    request.COOKIES['access_token'] = _encode(admin_user, settings.SECRET_KEY)

    response = _CookieController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_cookie_jwt_has_no_header_attributes() -> None:
    """Ensures cookie auth does not expose header-only attributes."""
    instance = CookieJWTSyncAuth()

    assert not hasattr(instance, 'auth_header')
    assert not hasattr(instance, 'auth_scheme')
    assert instance.cookie_name == 'access_token'


def test_header_jwt_bc_aliases() -> None:
    """Ensures the old `JWTSyncAuth` names keep working."""
    assert JWTSyncAuth is HeaderJWTSyncAuth
    assert JWTAsyncAuth is HeaderJWTAsyncAuth

    instance = JWTSyncAuth()

    assert isinstance(instance, JWTSyncAuth)
    assert isinstance(instance, BaseJWTSyncAuth)
    assert instance.auth_header == 'Authorization'
    assert instance.auth_scheme == 'Bearer'
