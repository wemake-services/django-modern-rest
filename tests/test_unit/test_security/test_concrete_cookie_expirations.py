import datetime as dt
from http import HTTPStatus
from typing import Any, Final

import jwt
import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from faker import Faker

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import concrete_views as jwt_views
from dmr.test import DMRRequestFactory

_COOKIE_VIEWS: Final = (
    jwt_views.CookieObtainTokensSyncController,
    jwt_views.CookieObtainTokensAsyncController,
    jwt_views.CookieRefreshTokensSyncController,
    jwt_views.CookieRefreshTokensAsyncController,
    jwt_views.CookieLogoutSyncController,
    jwt_views.CookieLogoutAsyncController,
)


def _assert_routable(routed_cls: type[Controller[Any]]) -> None:
    assert not routed_cls.is_abstract
    assert routed_cls.api_endpoints


_EXPIRATION: Final = dt.timedelta(minutes=5)
_REFRESH_EXPIRATION: Final = dt.timedelta(hours=1)


@pytest.mark.parametrize('view_cls', _COOKIE_VIEWS)
def test_as_view_with_expirations(
    *,
    view_cls: type[jwt_views.CookieObtainTokensSyncController[Any]],
) -> None:
    """Ensures that expirations of tokens and cookies go to the class."""
    view = view_cls.as_view(
        serializer=PydanticSerializer,
        jwt_expiration=_EXPIRATION,
        jwt_refresh_expiration=_REFRESH_EXPIRATION,
    )

    routed_cls = view.view_class  # type: ignore[attr-defined]
    _assert_routable(routed_cls)
    assert routed_cls.jwt_expiration == _EXPIRATION
    assert routed_cls.jwt_refresh_expiration == _REFRESH_EXPIRATION
    assert routed_cls.access_cookie_spec().max_age == int(
        _EXPIRATION.total_seconds(),
    )
    assert routed_cls.refresh_cookie_spec().max_age == int(
        _REFRESH_EXPIRATION.total_seconds(),
    )
    assert view_cls.jwt_expiration == dt.timedelta(days=1)
    assert view_cls.jwt_refresh_expiration == dt.timedelta(days=10)


@pytest.fixture
def password(faker: Faker) -> str:
    """Create a password for a user."""
    return faker.password()


@pytest.fixture
def user(faker: Faker, password: str) -> User:
    """Create fake user for tests."""
    return User.objects.create_user(
        username=faker.unique.user_name(),
        password=password,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('cookie_name', 'expiration'),
    [
        ('access_token', _EXPIRATION),
        ('refresh_token', _REFRESH_EXPIRATION),
    ],
)
def test_cookies_expire_with_tokens(
    *,
    dmr_rf: DMRRequestFactory,
    user: User,
    password: str,
    cookie_name: str,
    expiration: dt.timedelta,
) -> None:
    """Ensures that the cookies expire together with their tokens."""
    view = jwt_views.CookieObtainTokensSyncController.as_view(
        serializer=PydanticSerializer,
        jwt_expiration=_EXPIRATION,
        jwt_refresh_expiration=_REFRESH_EXPIRATION,
    )

    response = view(
        dmr_rf.post(
            '/whatever/',
            data={'username': user.username, 'password': password},
        ),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    cookie = response.cookies[cookie_name]
    claims = jwt.decode(cookie.value, options={'verify_signature': False})
    assert claims['exp'] - claims['iat'] == expiration.total_seconds()
    assert cookie['max-age'] == int(expiration.total_seconds())
