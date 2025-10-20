import json
from http import HTTPStatus
from typing import Final

import pytest
from django.http import HttpResponse

from django_modern_rest.openapi.converter import ConvertedSchema
from django_modern_rest.openapi.renderers import (
    BaseRenderer,
    JsonRenderer,
    SwaggerRenderer,
    json_serializer,
)
from django_modern_rest.test import DMRRequestFactory

_TEST_SCHEMA: Final[ConvertedSchema] = {  # noqa: WPS407
    'openapi': '3.1.0',
    'info': {'title': 'Test API', 'version': '1.0.0'},
    'paths': {
        '/test/': {
            'get': {
                'responses': {'200': {'description': 'Success'}},
            },
        },
    },
}


def test_json_serializer_basic_functionality() -> None:
    """Ensure that `json_serializer` converts schema to JSON string."""
    serialized = json_serializer(_TEST_SCHEMA)

    assert isinstance(serialized, str)
    assert json.loads(serialized) == _TEST_SCHEMA


@pytest.mark.parametrize(
    ('renderer_class', 'expected_content_type'),
    [
        (JsonRenderer, 'application/json'),
        (SwaggerRenderer, 'text/html'),
    ],
)
def test_renderer_content_types(
    *,
    renderer_class: type[BaseRenderer],
    expected_content_type: str,
) -> None:
    """Ensure that renderers have correct content types."""
    assert renderer_class().content_type == expected_content_type


@pytest.mark.parametrize(
    ('renderer_class', 'expected_path'),
    [
        (JsonRenderer, 'openapi.json/'),
        (SwaggerRenderer, 'swagger/'),
    ],
)
def test_renderer_default_paths(
    *,
    renderer_class: type[BaseRenderer],
    expected_path: str,
) -> None:
    """Ensure that renderers have correct default paths."""
    assert renderer_class.default_path == expected_path


@pytest.mark.parametrize(
    ('renderer_class', 'expected_name'),
    [
        (JsonRenderer, 'json'),
        (SwaggerRenderer, 'swagger'),
    ],
)
def test_renderer_default_names(
    *,
    renderer_class: type[BaseRenderer],
    expected_name: str,
) -> None:
    """Ensure that renderers have correct default names."""
    assert renderer_class.default_name == expected_name


def test_json_renderer_render_method(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that `JsonRenderer.render` returns correct JSON response."""
    renderer = JsonRenderer()
    request = dmr_rf.get('/test/')

    response = renderer.render(request, _TEST_SCHEMA)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'application/json'

    parsed_content = json.loads(response.content.decode('utf-8'))
    assert parsed_content == _TEST_SCHEMA


def test_swagger_renderer_render_method(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that `SwaggerRenderer.render` returns HTML response."""
    renderer = SwaggerRenderer()
    request = dmr_rf.get('/swagger/')

    response = renderer.render(request, _TEST_SCHEMA)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'text/html'

    content = response.content.decode('utf-8')  # noqa: WPS110
    assert 'swagger' in content.lower() or 'openapi' in content.lower()
