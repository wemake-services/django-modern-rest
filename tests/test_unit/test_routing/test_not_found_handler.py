from http import HTTPStatus

import pytest
from django.http import HttpRequest, HttpResponse
from django.urls import path
from inline_snapshot import snapshot

from dmr.exceptions import NotAcceptableError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.routing import build_404_handler
from dmr.test import DMRClient


def _view(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


urlpatterns = [
    path('api/existing/', _view),
    path('v1/existing/', _view),
    path('other/existing/', _view),
]

handler404 = build_404_handler('api/', serializer=PydanticSerializer)


@pytest.mark.urls(__name__)
def test_accept_json_returns(dmr_client: DMRClient) -> None:
    """Ensure that Accept: application/json returns JSON 404."""
    response = dmr_client.get(
        '/api/missing/',
        HTTP_ACCEPT='application/json',
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'
    assert response.json() == snapshot(
        {'detail': [{'msg': 'Page not found', 'type': 'not_found'}]},
    )


@pytest.mark.urls(__name__)
def test_fallback_html_not_found(dmr_client: DMRClient) -> None:
    """Ensure that falls back to default Django 404 for non-API paths."""
    response = dmr_client.get('/html/missing/')

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
    not_found_view = build_404_handler(prefix, serializer=PydanticSerializer)

    request = HttpRequest()
    request.path = '/api/missing/'

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
    not_found_view = build_404_handler(*prefixes, serializer=PydanticSerializer)

    request = HttpRequest()
    request.path = path
    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'].startswith(content_type)


def test_renderers_parameter() -> None:
    """Ensure that explicit renderers is used for negotiation."""
    not_found_view = build_404_handler(
        'api/',
        serializer=PydanticSerializer,
        renderers=[JsonRenderer()],
    )
    request = HttpRequest()
    request.path = '/api/missing/'
    # No Accept -> default (first) renderer
    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'


def test_handler_raises_not_acceptable() -> None:
    """Ensure that unsupported Accept leads to ``NotAcceptableError``."""
    not_found_view = build_404_handler('api/', serializer=PydanticSerializer)
    request = HttpRequest()
    request.path = '/api/missing/'
    request.META['HTTP_ACCEPT'] = 'text/plain'

    with pytest.raises(NotAcceptableError):
        not_found_view(request, Exception())


def test_no_accept_uses_default_renderer() -> None:
    """Ensure that missing Accept header uses first configured renderer."""
    not_found_view = build_404_handler('api/', serializer=PydanticSerializer)
    request = HttpRequest()
    request.path = '/api/missing/'
    # Ensure no Accept is set (e.g. new request may have no META)
    request.META.pop('HTTP_ACCEPT', None)

    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'
