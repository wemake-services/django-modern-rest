import json
from http import HTTPStatus

import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr.openapi import build_schema
from dmr.openapi.views import (
    OpenAPIJsonView,
    OpenAPIView,
    RedocView,
    ScalarView,
    SwaggerView,
)
from dmr.routing import Router
from dmr.test import DMRRequestFactory


def test_json_view(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that ``OpenAPIJsonView`` returns correct JSON response."""
    schema = build_schema(Router([], prefix=''))
    request = dmr_rf.get('/whatever/')

    response = OpenAPIJsonView.as_view(schema)(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'application/json'
    assert json.loads(response.content.decode('utf-8')) == snapshot({
        'openapi': '3.1.0',
        'info': {'title': 'Django Modern Rest', 'version': '0.1.0'},
        'paths': {},
        'components': {'schemas': {}, 'securitySchemes': {}},
    })


@pytest.mark.parametrize(
    'view_class',
    [RedocView, SwaggerView, ScalarView],
)
def test_html_view(
    dmr_rf: DMRRequestFactory,
    *,
    view_class: type[OpenAPIView],
) -> None:
    """Ensure that views return proper ``HTML`` response."""
    schema = build_schema(Router([], prefix=''))
    request = dmr_rf.get('/whatever/')

    response = view_class.as_view(schema)(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'text/html'
    assert '<html' in response.content.decode('utf-8').lower()
