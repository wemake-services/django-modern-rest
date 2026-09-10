import datetime as dt
from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from typing_extensions import override

from dmr.cookies import CookieSpec
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt.token import JWToken
from dmr.security.jwt.views import (  # noqa: WPS235
    CookieLogoutSyncController,
    CookieObtainTokensSyncController,
    CookieRefreshTokensAsyncController,
    CookieRefreshTokensSyncController,
    ObtainTokensPayload,
)
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory

if TYPE_CHECKING:
    from tests.test_unit.conftest import CsrfFailureAssertion

_REFRESH_PATH: Final = '/api/auth/refresh/'


class _ObtainController(
    CookieObtainTokensSyncController[
        PydanticFastSerializer,
        ObtainTokensPayload,
    ],
):
    jwt_refresh_cookie_path = _REFRESH_PATH

    @override
    def convert_auth_payload(
        self,
        payload: ObtainTokensPayload,
    ) -> ObtainTokensPayload:
        return payload


class _CustomObtainController(_ObtainController):
    jwt_access_cookie = 'my_access'
    jwt_refresh_cookie = 'my_refresh'
    jwt_access_cookie_path = '/api/'
    jwt_cookie_domain = 'example.com'
    jwt_cookie_samesite = 'strict'
    jwt_expiration = dt.timedelta(minutes=5)
    jwt_refresh_expiration = dt.timedelta(hours=1)


class _RefreshController(
    CookieRefreshTokensSyncController[PydanticFastSerializer],
):
    jwt_refresh_cookie_path = _REFRESH_PATH


class _AsyncRefreshController(
    CookieRefreshTokensAsyncController[PydanticFastSerializer],
):
    jwt_refresh_cookie_path = _REFRESH_PATH


class _LogoutController(CookieLogoutSyncController[PydanticFastSerializer]):
    jwt_refresh_cookie_path = _REFRESH_PATH


class _NoCsrfLogoutController(_LogoutController):
    jwt_ensure_csrf = False


@pytest.mark.parametrize(
    'controller',
    [_ObtainController, _RefreshController, _LogoutController],
)
def test_cookie_defaults_are_safe(
    *,
    controller: type[CookieLogoutSyncController[PydanticFastSerializer]],
) -> None:
    """Ensures that the default cookie flags cannot leak the tokens."""
    for cookie_spec in controller.issued_cookies_spec().values():
        assert cookie_spec.httponly
        assert cookie_spec.secure
        assert cookie_spec.samesite == 'lax'

    assert controller.access_cookie_spec().path == '/'
    assert controller.refresh_cookie_spec().path == _REFRESH_PATH


def test_cookie_max_age_follows_expiration() -> None:
    """Ensures that cookies live exactly as long as their tokens."""
    assert _ObtainController.access_cookie_spec().max_age == int(
        dt.timedelta(days=1).total_seconds(),
    )
    assert _ObtainController.refresh_cookie_spec().max_age == int(
        dt.timedelta(days=10).total_seconds(),
    )
    assert _CustomObtainController.access_cookie_spec().max_age == int(
        dt.timedelta(minutes=5).total_seconds(),
    )
    assert _CustomObtainController.refresh_cookie_spec().max_age == int(
        dt.timedelta(hours=1).total_seconds(),
    )


def test_customized_cookies_reach_the_spec() -> None:
    """Ensures that class-level settings end up in the endpoint metadata."""
    metadata = _CustomObtainController.api_endpoints['POST'].metadata
    cookies = metadata.responses[HTTPStatus.NO_CONTENT].cookies

    assert cookies is not None
    assert cookies['my_access'] == CookieSpec(
        path='/api/',
        max_age=int(dt.timedelta(minutes=5).total_seconds()),
        domain='example.com',
        secure=True,
        httponly=True,
        samesite='strict',
        description=cookies['my_access'].description,
    )
    assert cookies['my_refresh'].path == _REFRESH_PATH
    assert 'csrftoken' in cookies


def test_discarded_cookies_expire_right_away() -> None:
    """Ensures that logout cookies tell the browser to drop them."""
    metadata = _LogoutController.api_endpoints['POST'].metadata
    cookies = metadata.responses[HTTPStatus.NO_CONTENT].cookies

    assert cookies is not None
    assert cookies.keys() == {'access_token', 'refresh_token'}
    for cookie_spec in cookies.values():
        assert cookie_spec.max_age == 0
        assert cookie_spec.httponly
        assert cookie_spec.secure


@pytest.mark.parametrize(
    ('controller', 'has_csrf_response'),
    [
        (_RefreshController, True),
        (_LogoutController, True),
        (_NoCsrfLogoutController, False),
        (_ObtainController, False),
    ],
)
def test_csrf_response_is_documented(
    *,
    controller: type[CookieLogoutSyncController[PydanticFastSerializer]],
    has_csrf_response: bool,
) -> None:
    """Ensures that the CSRF failure is only documented when it can happen."""
    metadata = controller.api_endpoints['POST'].metadata

    assert (HTTPStatus.FORBIDDEN in metadata.responses) is has_csrf_response


def test_no_csrf_cookie_with_sessions(
    settings: LazySettings,
) -> None:
    """Ensures that there is no CSRF cookie with ``CSRF_USE_SESSIONS``."""
    settings.CSRF_USE_SESSIONS = True

    assert _ObtainController.csrf_cookie_spec() == {}


@pytest.mark.django_db
def test_obtain_sets_cookies(
    dmr_rf: DMRRequestFactory,
    admin_user: User,
) -> None:
    """Ensures that a login issues both cookies."""
    request = dmr_rf.post(
        '/whatever/',
        data={'username': admin_user.username, 'password': 'password'},
    )

    response = _ObtainController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.cookies.keys() == {'access_token', 'refresh_token'}


@pytest.mark.django_db
def test_refresh_of_a_deleted_user(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
    fill_csrf: Callable[[HttpRequest], HttpRequest],
) -> None:
    """Ensures that a token of a missing user is rejected."""
    request = fill_csrf(dmr_rf.post('/whatever/'))
    request.COOKIES['refresh_token'] = JWToken(
        sub='404',
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        extras={'type': 'refresh'},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    response = _RefreshController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert not response.cookies


# `None` means "the real user's pk" and is the control case.
# It is also required for coverage: on python 3.11 the lines after
# `await` are not traced when the awaited coroutine is resumed with
# an exception thrown in from the thread that `aget` runs in.
# The failing cases alone would leave the assertions below unmeasured.
_ASYNC_REFRESH_CASES: Final = (
    (None, HTTPStatus.NO_CONTENT, {'access_token', 'refresh_token'}),
    ('404', HTTPStatus.UNAUTHORIZED, set()),
)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ('subject', 'expected_status', 'expected_cookies'),
    _ASYNC_REFRESH_CASES,
)
async def test_async_refresh(
    dmr_async_rf: DMRAsyncRequestFactory,
    admin_user: User,
    settings: LazySettings,
    fill_csrf: Callable[[HttpRequest], HttpRequest],
    *,
    subject: str | None,
    expected_status: HTTPStatus,
    expected_cookies: set[str],
) -> None:
    """Ensures that only an existing user can refresh, async case."""
    request = fill_csrf(dmr_async_rf.post('/whatever/'))
    request.COOKIES['refresh_token'] = JWToken(
        sub=subject or str(admin_user.pk),
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
        extras={'type': 'refresh'},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    response = await dmr_async_rf.wrap(
        _AsyncRefreshController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == expected_status, response.content
    assert response.cookies.keys() == expected_cookies


@pytest.mark.django_db
def test_logout_checks_csrf(
    dmr_rf: DMRRequestFactory,
    assert_csrf_failure_message: 'CsrfFailureAssertion',
) -> None:
    """Ensures that logout does not act on cookies of a forged request."""
    request = dmr_rf.post('/whatever/')

    response = _LogoutController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN, response.content
    assert not response.cookies
    assert_csrf_failure_message(response)


@pytest.mark.django_db
def test_logout_without_csrf_check(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that the CSRF check can be turned off."""
    request = dmr_rf.post('/whatever/')

    response = _NoCsrfLogoutController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.cookies.keys() == {'access_token', 'refresh_token'}
    for cookie in response.cookies.values():
        assert not cookie.value
        assert cookie['max-age'] == 0


@pytest.mark.parametrize(
    'base',
    [
        CookieRefreshTokensSyncController,
        CookieLogoutSyncController,
    ],
)
def test_refresh_cookie_path_is_required(
    *,
    base: type[CookieLogoutSyncController[PydanticFastSerializer]],
) -> None:
    """Ensures that we don't silently send the refresh token everywhere."""
    with pytest.raises(EndpointMetadataError, match='jwt_refresh_cookie_path'):

        class _BrokenController(base[PydanticFastSerializer]):  # type: ignore[misc, valid-type]
            """Missing `jwt_refresh_cookie_path` here."""
