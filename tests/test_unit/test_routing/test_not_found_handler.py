from http import HTTPStatus

import pytest
from django.http import HttpRequest, HttpResponse
from django.urls import path
from inline_snapshot import snapshot

from dmr.routing import build_404_handler
from dmr.test import DMRClient


def _view(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


urlpatterns = [
    path('api/existing/', _view),
    path('v1/existing/', _view),
    path('other/existing/', _view),
]

handler404 = build_404_handler('api/')


@pytest.mark.urls(__name__)
def test_api_json_not_found(dmr_client: DMRClient) -> None:
    """Esure that handler returns JSON 404 for API prefix."""
    response = dmr_client.get('/api/missing/')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'
    assert response.json() == snapshot(
        {'detail': [{'msg': 'Page not found', 'type': 'not_found'}]},
    )


@pytest.mark.urls(__name__)
def test_fallback_html_not_found(dmr_client: DMRClient) -> None:
    """Ensure that falls back to default Django 404 for non-API paths."""
    response = dmr_client.get('/missing/')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'].startswith('text/html')


@pytest.mark.urls(__name__)
def test_existing_ok(dmr_client: DMRClient) -> None:
    """Ensure that does not affect existing routes."""
    response = dmr_client.get('/api/existing/')

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize('prefix', ['api', '/api', 'api/', '/api/'])
def test_prefix_normalization(prefix: str) -> None:
    """Ensure that normalizes prefix with or without slashes."""
    not_found_view = build_404_handler(prefix)

    request = HttpRequest()
    request.path = '/api/test/'

    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'


@pytest.mark.parametrize(
    ('prefixes', 'path', 'content_type'),
    [
        (('api/', 'v1/'), '/v1/missing/', 'application/json'),
        (('api/', 'v1/'), '/other/missing/', 'text/html'),
        (('api',), '/apiary/test/', 'application/json'),
    ],
)
def test_prefix_matching(
    prefixes: tuple[str, ...],
    path: str,
    content_type: str,
) -> None:
    """Ensure correct prefix matching and fallback behavior."""
    not_found_view = build_404_handler(*prefixes)

    request = HttpRequest()
    request.path = path
    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'].startswith(content_type)
