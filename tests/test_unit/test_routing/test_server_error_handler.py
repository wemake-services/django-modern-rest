import json
from http import HTTPStatus
from typing import Any

import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr.errors import ErrorType
from dmr.negotiation import request_renderer
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.routing import build_500_handler
from dmr.test import DMRRequestFactory
from tests.infra.xml_format import XmlRenderer


@pytest.mark.parametrize('prefix', ['api', '/api', 'api/', '/api/'])
def test_prefix_normalization(
    dmr_rf: DMRRequestFactory,
    *,
    prefix: str,
) -> None:
    """Ensure that normalizes prefix with or without slashes."""
    view = build_500_handler(prefix, serializer=PydanticSerializer)
    request = dmr_rf.get('/api/existing/')

    response = view(request)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error', 'type': 'internal_error'}],
    })


@pytest.mark.parametrize(
    ('prefixes', 'path', 'content_type'),
    [
        (('api/', 'v1/'), '/v1/existing/', 'application/json'),
        (('api/', 'v1/'), '/other/existing/', 'text/html'),
    ],
)
def test_multiple_prefixes(
    dmr_rf: DMRRequestFactory,
    *,
    prefixes: tuple[str, ...],
    path: str,
    content_type: str,
) -> None:
    """Ensure correct prefix matching and fallback behavior."""
    view = build_500_handler(*prefixes, serializer=PydanticSerializer)
    request = dmr_rf.get(path)

    response = view(request)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response['Content-Type'].startswith(content_type)


def test_renderers_parameter(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that explicit renderers is used for negotiation."""
    view = build_500_handler(
        'api/',
        serializer=PydanticSerializer,
        renderers=[JsonRenderer()],
    )
    request = dmr_rf.get('/api/existing/')

    response = view(request)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error', 'type': 'internal_error'}],
    })


def test_no_accept_uses_default_renderer(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that missing Accept header uses first configured renderer."""
    view = build_500_handler('api/', serializer=PydanticSerializer)
    request = dmr_rf.get('/api/existing/', headers={'Accept': None})

    response = view(request)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error', 'type': 'internal_error'}],
    })


def _format_error(
    error: str | Exception,
    *,
    loc: str | None = None,
    error_type: str | ErrorType | None = None,
) -> dict[str, str]:
    return {'message': str(error)}


def test_format_error_parameter(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that custom ``format_error`` function is used."""
    view = build_500_handler(
        'api/',
        serializer=PydanticSerializer,
        format_error=_format_error,
    )
    request = dmr_rf.get('/api/existing/')

    response = view(request)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'message': 'Internal server error',
    })


@pytest.mark.parametrize(
    ('request_headers', 'expected_headers', 'expected_data'),
    [
        (
            {'Accept': 'application/json'},
            {'Content-Type': 'application/json'},
            (
                b'{"detail":[{"msg":"Internal server error",'
                b'"type":"internal_error"}]}'
            ),
        ),
        (
            {'Accept': 'application/xml'},
            {'Content-Type': 'application/xml'},
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n'
                b'<detail>\n\t<msg>Internal server error</msg>\n\t'
                b'<type>internal_error</type>\n</detail>'
            ),
        ),
        (
            {'Accept': 'application/xml, application/json'},
            {'Content-Type': 'application/xml'},
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n'
                b'<detail>\n\t<msg>Internal server error</msg>\n\t'
                b'<type>internal_error</type>\n</detail>'
            ),
        ),
        (
            {'Accept': 'application/json, application/xml'},
            {'Content-Type': 'application/json'},
            (
                b'{"detail":[{"msg":"Internal server error",'
                b'"type":"internal_error"}]}'
            ),
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
    """Ensure 500 response format follows ``Accept`` header."""
    view = build_500_handler(
        'api/',
        serializer=PydanticSerializer,
        renderers=[XmlRenderer(), JsonRenderer()],
    )
    request = dmr_rf.get('/api/existing/', headers=request_headers)

    response = view(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.headers == expected_headers
    assert response.content == expected_data


def test_not_acceptable(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that wrong ``Accept`` takes the priority."""
    view = build_500_handler(
        'api/',
        serializer=PydanticSerializer,
    )
    request = dmr_rf.get('/api/existing/', headers={'Accept': 'wrong'})

    response = view(request)

    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
    assert request_renderer(request) is None
    with pytest.raises(AttributeError, match='__dmr_renderer__'):
        request_renderer(request, strict=True)
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Cannot serialize response body with accepted types '
                    "[<MediaType: wrong>], supported=['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })
