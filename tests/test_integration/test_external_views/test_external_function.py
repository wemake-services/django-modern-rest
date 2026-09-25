from http import HTTPStatus

from django.urls import reverse
from inline_snapshot import snapshot

from dmr.test import DMRClient


def test_external_function_success(dmr_client: DMRClient) -> None:
    """Ensure that success path works."""
    response = dmr_client.get(
        reverse('api:external_views:external_function'),
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({'status': 200})


def test_external_function_bad_method(dmr_client: DMRClient) -> None:
    """Ensure that wrong method raises 405."""
    response = dmr_client.post(
        reverse('api:external_views:external_function'),
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED, (
        response.content
    )
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {}
