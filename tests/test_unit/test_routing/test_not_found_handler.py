import json
from http import HTTPStatus
from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.urls import path
from inline_snapshot import snapshot

from dmr.errors import ErrorType
from dmr.exceptions import NotAcceptableError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.routing import build_404_handler
from dmr.test import DMRClient, DMRRequestFactory
from tests.infra.xml_format import XmlRenderer


def _simple_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


urlpatterns = [
    path('api/existing/', _simple_view),
    path('v1/existing/', _simple_view),
    path('other/existing/', _simple_view),
]
handler404 = build_404_handler('api/', serializer=PydanticSerializer)


@pytest.mark.urls(__name__)
def test_accept_json_returns(dmr_client: DMRClient) -> None:
    """Ensure that Accept: application/json returns JSON 404."""
    response = dmr_client.get(
        '/api/missing/',
        headers={'Accept': 'application/json'},
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
def test_existing_success(dmr_client: DMRClient) -> None:
    """Ensure that does not affect existing routes."""
    response = dmr_client.get('/api/existing/')

    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize('prefix', ['api', '/api', 'api/', '/api/'])
def test_prefix_normalization(
    dmr_rf: DMRRequestFactory,
    *,
    prefix: str,
) -> None:
    """Ensure that normalizes prefix with or without slashes."""
    not_found_view = build_404_handler(prefix, serializer=PydanticSerializer)
    request = dmr_rf.get('/api/missing/')

    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot(
        {'detail': [{'msg': 'Page not found', 'type': 'not_found'}]},
    )


@pytest.mark.parametrize(
    ('prefixes', 'path', 'content_type'),
    [
        (('api/', 'v1/'), '/v1/missing/', 'application/json'),
        (('api/', 'v1/'), '/other/missing/', 'text/html'),
        (('api',), '/apiary/test/', 'application/json'),
    ],
)
def test_prefix_matching(
    dmr_rf: DMRRequestFactory,
    *,
    prefixes: tuple[str, ...],
    path: str,
    content_type: str,
) -> None:
    """Ensure correct prefix matching and fallback behavior."""
    not_found_view = build_404_handler(*prefixes, serializer=PydanticSerializer)
    request = dmr_rf.get(path)

    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'].startswith(content_type)


def test_renderers_parameter(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that explicit renderers is used for negotiation."""
    not_found_view = build_404_handler(
        'api/',
        serializer=PydanticSerializer,
        renderers=[JsonRenderer()],
    )
    request = dmr_rf.get('/api/missing/')

    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot(
        {'detail': [{'msg': 'Page not found', 'type': 'not_found'}]},
    )


def test_handler_raises_not_acceptable(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that unsupported Accept leads to ``NotAcceptableError``."""
    not_found_view = build_404_handler(
        'api/',
        serializer=PydanticSerializer,
        renderers=[XmlRenderer()],
    )
    request = dmr_rf.get(
        '/api/missing/',
        headers={'Accept': 'application/json'},
    )

    with pytest.raises(
        NotAcceptableError,
        match='Cannot serialize response body with accepted types',
    ):
        not_found_view(request, Exception())


def test_no_accept_uses_default_renderer(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that missing Accept header uses first configured renderer."""
    not_found_view = build_404_handler('api/', serializer=PydanticSerializer)
    request = dmr_rf.get('/api/missing/', headers={'Accept': None})

    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot(
        {'detail': [{'msg': 'Page not found', 'type': 'not_found'}]},
    )


def _format_error(
    error: str | Exception,
    *,
    loc: str | None = None,
    error_type: str | ErrorType | None = None,
) -> dict[str, str]:
    return {'message': str(error)}


def test_format_error_parameter(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that custom ``format_error`` function is used."""
    not_found_view = build_404_handler(
        'api/',
        serializer=PydanticSerializer,
        format_error=_format_error,
    )
    request = dmr_rf.get('/api/missing/')

    response = not_found_view(request, Exception())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot(
        {'message': 'Page not found'},
    )


@pytest.mark.parametrize(
    ('request_headers', 'expected_headers', 'expected_data'),
    [
        (
            {'Accept': 'application/json'},
            {'Content-Type': 'application/json'},
            b'{"detail": [{"msg": "Page not found", "type": "not_found"}]}',
        ),
        (
            {'Accept': 'application/xml'},
            {'Content-Type': 'application/xml'},
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t<msg>'
                b'Page not found</msg>\n\t<type>not_found</type>\n</detail>'
            ),
        ),
        (
            {'Accept': 'application/xml, application/json'},
            {'Content-Type': 'application/xml'},
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t<msg>'
                b'Page not found</msg>\n\t<type>not_found</type>\n</detail>'
            ),
        ),
        (
            {'Accept': 'application/json, application/xml'},
            {'Content-Type': 'application/json'},
            b'{"detail": [{"msg": "Page not found", "type": "not_found"}]}',
        ),
    ],
)
def test_not_found_format_by_accept_header(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    expected_headers: dict[str, str],
    expected_data: Any,
) -> None:
    """Ensure 404 response format follows ``Accept`` header."""
    not_found_view = build_404_handler(
        'api/',
        serializer=PydanticSerializer,
        renderers=[XmlRenderer(), JsonRenderer()],
    )
    request = dmr_rf.get('/api/missing/', headers=request_headers)

    response = not_found_view(request, Exception())

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert dict(response.headers) == expected_headers
    assert response.content == expected_data
