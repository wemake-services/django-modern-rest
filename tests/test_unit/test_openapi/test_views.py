import json
from http import HTTPStatus

import pytest
import yaml
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr.openapi import build_schema
from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.views import (
    OpenAPIJsonView,
    OpenAPIView,
    RedocView,
    ScalarView,
    StoplightView,
    SwaggerView,
)
from dmr.openapi.views.yaml import OpenAPIYamlView
from dmr.routing import Router
from dmr.test import DMRRequestFactory


def test_json_view(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that ``OpenAPIJsonView`` returns correct JSON response."""
    schema = build_schema(Router('', []))
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


def test_yaml_view(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that ``OpenAPIYamlView`` returns correct YAML response."""
    schema = build_schema(Router('', []))
    request = dmr_rf.get('/whatever/')

    response = OpenAPIYamlView.as_view(schema)(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'application/yaml'
    assert yaml.safe_load(response.content) == snapshot({
        'components': {'schemas': {}, 'securitySchemes': {}},
        'info': {'title': 'Django Modern Rest', 'version': '0.1.0'},
        'openapi': '3.1.0',
        'paths': {},
    })


@pytest.mark.parametrize(
    'view_class',
    [RedocView, SwaggerView, ScalarView, StoplightView],
)
def test_html_view(
    dmr_rf: DMRRequestFactory,
    *,
    view_class: type[OpenAPIView],
) -> None:
    """Ensure that views return proper ``HTML`` response."""
    schema = build_schema(Router('', []))
    request = dmr_rf.get('/whatever/')

    response = view_class.as_view(schema)(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'text/html'
    assert '<html' in response.content.decode('utf-8').lower()


@pytest.mark.parametrize(
    'view_class',
    [
        RedocView,
        SwaggerView,
        ScalarView,
        StoplightView,
        OpenAPIJsonView,
        OpenAPIYamlView,
    ],
)
def test_skip_validation(
    dmr_rf: DMRRequestFactory,
    *,
    view_class: type[OpenAPIView],
) -> None:
    """Ensure that views can skip validation."""
    schema = build_schema(
        Router('', []),
        config=OpenAPIConfig(title='A', version='B', openapi_version='wrong'),
    )
    request = dmr_rf.get('/whatever/')

    response = view_class.as_view(schema, skip_validation=True)(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
