import json
from http import HTTPStatus
from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import override_settings
from django.urls import path, reverse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.security.csrf import build_csrf_handler
from dmr.test import DMRClient, DMRRequestFactory
from tests.infra.xml_format import XmlRenderer


class _CsrfController(Controller[PydanticSerializer]):
    csrf_exempt = False

    def post(self) -> str:
        raise NotImplementedError


def _simple_view(request: HttpRequest) -> HttpResponse:
    raise NotImplementedError


urlpatterns = [
    path('api/csrf/', _CsrfController.as_view(), name='csrf'),
    path('api/other-csrf/', _CsrfController.as_view(), name='other-csrf'),
    path('other/existing/', _simple_view, name='not-api'),
]
csrf_hander = build_csrf_handler('api/', serializer=PydanticSerializer)


@override_settings(ROOT_URLCONF=__name__, CSRF_FAILURE_VIEW=csrf_hander)
def test_accept_json_returns() -> None:
    """Ensure that Accept: application/json returns JSON 403."""
    dmr_client = DMRClient(enforce_csrf_checks=True)

    response = dmr_client.post(
        reverse('csrf'),
        headers={'Accept': 'application/json'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response['Content-Type'] == 'application/json'
    assert response.json() == snapshot({'detail': [{'msg': 'CSRF Failed.'}]})


@override_settings(ROOT_URLCONF=__name__, CSRF_FAILURE_VIEW=csrf_hander)
def test_fallback_html_forbidden() -> None:
    """Ensure that falls back to default Django 403 for non-API paths."""
    dmr_client = DMRClient(enforce_csrf_checks=True)

    response = dmr_client.post(
        reverse('not-api'),
        headers={'Accept': 'application/json'},
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response['Content-Type'].startswith('text/html')


@override_settings(ROOT_URLCONF=__name__, CSRF_FAILURE_VIEW=csrf_hander)
def test_unsupported_accept_header(dmr_client: DMRClient) -> None:
    """Ensure that unsupported ``Accept`` returns correct error message."""
    dmr_client = DMRClient(enforce_csrf_checks=True)

    response = dmr_client.post(
        reverse('csrf'),
        headers={'Accept': 'wrong'},
    )

    assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
    assert response['Content-Type'] == 'application/json'
    assert response.json() == snapshot({
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


@pytest.mark.parametrize('prefix', ['api', '/api', 'api/', '/api/'])
def test_prefix_normalization(
    dmr_rf: DMRRequestFactory,
    *,
    prefix: str,
) -> None:
    """Ensure that normalizes prefix with or without slashes."""
    csrf_error_view = build_csrf_handler(prefix, serializer=PydanticSerializer)
    request = dmr_rf.get('/api/whatever/')

    response = csrf_error_view(request)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'CSRF Failed.'}],
    })


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
    csrf_error_view = build_csrf_handler(
        *prefixes,
        serializer=PydanticSerializer,
    )
    request = dmr_rf.post(path)

    response = csrf_error_view(request)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response['Content-Type'].startswith(content_type)


def test_no_accept_uses_default_renderer(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that missing Accept header uses first configured renderer."""
    csrf_error_view = build_csrf_handler('api/', serializer=PydanticSerializer)
    request = dmr_rf.get(
        '/api/missing/',
        headers={'Accept': None},  # type: ignore[dict-item]
    )

    response = csrf_error_view(request)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'CSRF Failed.'}],
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
    csrf_error_view = build_csrf_handler(
        'api/',
        serializer=PydanticSerializer,
        format_error=_format_error,
    )
    request = dmr_rf.post('/api/missing/')

    response = csrf_error_view(request)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({'message': 'CSRF Failed.'})


@pytest.mark.parametrize(
    ('request_headers', 'expected_headers', 'expected_data'),
    [
        (
            {'Accept': 'application/json'},
            {'Content-Type': 'application/json'},
            b'{"detail":[{"msg":"CSRF Failed."}]}',
        ),
        (
            {'Accept': 'application/xml'},
            {'Content-Type': 'application/xml'},
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t'
                b'<msg>CSRF Failed.</msg>\n</detail>'
            ),
        ),
        (
            {'Accept': 'application/xml, application/json'},
            {'Content-Type': 'application/xml'},
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t'
                b'<msg>CSRF Failed.</msg>\n</detail>'
            ),
        ),
        (
            {'Accept': 'application/json, application/xml'},
            {'Content-Type': 'application/json'},
            b'{"detail":[{"msg":"CSRF Failed."}]}',
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
    csrf_error_view = build_csrf_handler(
        'api/',
        serializer=PydanticSerializer,
        renderers=[XmlRenderer(), JsonRenderer()],
    )
    request = dmr_rf.post('/api/missing/', headers=request_headers)

    response = csrf_error_view(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.headers == expected_headers
    assert response.content == expected_data
