from http import HTTPStatus

import django
import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import override_settings
from django.urls import reverse

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import path
from dmr.security import request_auth
from dmr.security.django_session import DjangoSessionSyncAuth
from dmr.test import DMRClient


class _PublicController(Controller[PydanticFastSerializer]):
    def get(self) -> str:
        return 'ok'


class _LoginRequiredController(Controller[PydanticFastSerializer]):
    login_required = True

    def get(self) -> str:
        return 'ok'


class _SessionAuthController(Controller[PydanticFastSerializer]):
    auth = [DjangoSessionSyncAuth()]

    def get(self) -> str:
        return 'ok'


urlpatterns = [
    path('api/public/', _PublicController.as_view(), name='public'),
    path('api/session/', _SessionAuthController.as_view(), name='session'),
    path(
        'api/private/',
        _LoginRequiredController.as_view(),
        name='private',
    ),
]


@pytest.mark.parametrize(
    'controller',
    [
        _PublicController,
        _SessionAuthController,
        _LoginRequiredController,
    ],
)
def test_controller_login_required_attribute(
    controller: type[Controller[PydanticFastSerializer]],
) -> None:
    """Ensure the generated view exposes the controller's login_required."""
    assert controller.as_view().login_required is controller.login_required  # type: ignore[attr-defined]


@pytest.mark.skipif(
    django.VERSION < (5, 1),
    reason='LoginRequiredMiddleware was added in Django 5.1',
)
@override_settings(
    ROOT_URLCONF=__name__,
    LOGIN_URL='/login/',
    MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.LoginRequiredMiddleware',
    ],
)
@pytest.mark.parametrize(
    ('view_name', 'status_code'),
    [('public', HTTPStatus.OK), ('private', HTTPStatus.FOUND)],
)
def test_controller_login_required_anonymous(
    view_name: str,
    status_code: HTTPStatus,
) -> None:
    """Ensure anonymous access respects the controller's login requirement."""
    response = DMRClient().get(reverse(view_name))

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content
    if status_code == HTTPStatus.FOUND:
        assert response.headers['Location'] == '/login/?next=/api/private/'
    else:
        assert response.json() == 'ok'


@pytest.mark.skipif(
    django.VERSION < (5, 1),
    reason='LoginRequiredMiddleware was added in Django 5.1',
)
@override_settings(
    ROOT_URLCONF=__name__,
    LOGIN_URL='/login/',
    MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.LoginRequiredMiddleware',
    ],
)
def test_controller_login_required_session_auth() -> None:
    """Ensure DMR session auth rejects anonymous users without redirecting."""
    response = DMRClient().get(reverse('session'))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert 'Location' not in response.headers
    assert response.json() == {
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    }


@pytest.mark.skipif(
    django.VERSION < (5, 1),
    reason='LoginRequiredMiddleware was added in Django 5.1',
)
@pytest.mark.django_db
@override_settings(
    ROOT_URLCONF=__name__,
    LOGIN_URL='/login/',
    MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.LoginRequiredMiddleware',
    ],
)
def test_controller_login_required_authenticated() -> None:
    """Ensure authenticated users can access a login-required controller."""
    user = User.objects.create_user(username='test-user')
    client = DMRClient()
    client.force_login(user)

    response = client.get(reverse('private'))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.content == b'"ok"'


@pytest.mark.skipif(
    django.VERSION < (5, 1),
    reason='LoginRequiredMiddleware was added in Django 5.1',
)
@pytest.mark.django_db
@override_settings(
    ROOT_URLCONF=__name__,
    LOGIN_URL='/login/',
    MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.LoginRequiredMiddleware',
    ],
)
def test_controller_session_auth_authenticated() -> None:
    """Ensure authenticated users pass middleware and DMR session auth."""
    user = User.objects.create_user(username='test-user')
    client = DMRClient()
    client.force_login(user)

    response = client.get(reverse('session'))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.content == b'"ok"'
    assert isinstance(
        request_auth(response.wsgi_request),
        DjangoSessionSyncAuth,
    )
