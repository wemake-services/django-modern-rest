from collections.abc import Callable
from http import HTTPStatus

from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import _get_new_csrf_string, _mask_cipher_secret  # type: ignore[attr-defined]
from django.test import override_settings
from django.urls import reverse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.routing import path
from dmr.security.csrf import build_csrf_handler
from dmr.test import DMRClient


class _CsrfController(Controller[PydanticFastSerializer]):
    csrf_exempt = False

    def post(self) -> str:
        return 'ok'


class _NoCsrfController(Controller[PydanticFastSerializer]):
    def post(self) -> str:
        return 'ok'


urlpatterns = [
    path('api/csrf/', _CsrfController.as_view(), name='csrf'),
    path('api/no-csrf/', _NoCsrfController.as_view(), name='no-csrf'),
]

csrf_hander = build_csrf_handler('api/', serializer=PydanticFastSerializer)


@override_settings(ROOT_URLCONF=__name__, CSRF_FAILURE_VIEW=csrf_hander)
def test_csrf_controller() -> None:
    """Ensure that `csrf_exempt=False` on controller is supported."""
    dmr_client = DMRClient(enforce_csrf_checks=True)

    response = dmr_client.post(reverse('csrf'), data={})

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({'detail': [{'msg': 'CSRF Failed.'}]})


@override_settings(ROOT_URLCONF=__name__, CSRF_FAILURE_VIEW=csrf_hander)
def test_csrf_controller_valid(
    fill_csrf: Callable[[HttpRequest], HttpRequest],
) -> None:
    """Ensure that `csrf_exempt=False` on controller is supported."""
    dmr_client = DMRClient(enforce_csrf_checks=True)
    secret = _get_new_csrf_string()
    token = _mask_cipher_secret(secret)
    dmr_client.cookies['csrftoken'] = secret

    response = dmr_client.post(
        reverse('csrf'),
        data={},
        HTTP_X_CSRFTOKEN=token,
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot('ok')


@override_settings(ROOT_URLCONF=__name__, CSRF_FAILURE_VIEW=csrf_hander)
def test_csrf_controller_exempt() -> None:
    """Ensure that `csrf_exempt=True` on controller is supported."""
    dmr_client = DMRClient(enforce_csrf_checks=True)

    response = dmr_client.post(reverse('no-csrf'))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot('ok')
