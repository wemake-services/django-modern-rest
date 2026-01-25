import importlib
import json
import sys
from http import HTTPStatus
from types import ModuleType, SimpleNamespace
from typing import Any, Final, cast

import pytest
from _pytest.monkeypatch import MonkeyPatch
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt

from django_modern_rest.openapi.converter import ConvertedSchema
from django_modern_rest.openapi.objects.open_api import _OPENAPI_VERSION
from django_modern_rest.openapi.renderers import (
    BaseRenderer,
    JsonRenderer,
    RedocRenderer,
    ScalarRenderer,
    SwaggerRenderer,
    json_serializer,
)
from django_modern_rest.test import DMRRequestFactory

_TEST_SCHEMA: Final[ConvertedSchema] = {  # noqa: WPS407
    'openapi': _OPENAPI_VERSION,
    'info': {'title': 'Test API', 'version': '1.0.0'},
    'paths': {
        '/test/': {
            'get': {
                'responses': {'200': {'description': 'Success'}},
            },
        },
    },
}

JSON_MODULE: Final = 'django_modern_rest.internal.json'
BASE_MODULE: Final = 'django_modern_rest.openapi.renderers.base'


def test_json_serializer_basic_functionality() -> None:
    """Ensure that `json_serializer` converts schema to JSON string."""
    serialized = json_serializer(_TEST_SCHEMA)

    assert isinstance(serialized, str)
    assert json.loads(serialized) == _TEST_SCHEMA


@pytest.mark.parametrize(
    ('renderer_class', 'expected_content_type'),
    [
        (JsonRenderer, 'application/json'),
        (RedocRenderer, 'text/html'),
        (SwaggerRenderer, 'text/html'),
        (ScalarRenderer, 'text/html'),
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
        (RedocRenderer, 'redoc/'),
        (SwaggerRenderer, 'swagger/'),
        (ScalarRenderer, 'scalar/'),
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
        (RedocRenderer, 'redoc'),
        (SwaggerRenderer, 'swagger'),
        (ScalarRenderer, 'scalar'),
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


@pytest.mark.parametrize(
    'renderer_class',
    [RedocRenderer, SwaggerRenderer, ScalarRenderer],
)
def test_html_renderer_render_method(
    dmr_rf: DMRRequestFactory,
    *,
    renderer_class: type[BaseRenderer],
) -> None:
    """Ensure that HTML renderers return proper HTML response."""
    renderer = renderer_class()
    request = dmr_rf.get(f'/{renderer.default_path}')

    response = renderer.render(request, _TEST_SCHEMA)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert response['Content-Type'] == 'text/html'
    assert '<html' in response.content.decode('utf-8').lower()


@pytest.mark.parametrize(
    ('decorators', 'expected_len'),
    [
        ([], 0),
        ([csrf_exempt], 1),
        ([login_required, cache_page(10)], 2),
        ([csrf_exempt, login_required], 2),
    ],
)
def test_renderer_with_simple_decorators(
    *,
    decorators: list[Any] | None,
    expected_len: int | None,
) -> None:
    """Ensure that simple Django decorators work with renderers."""
    renderer = JsonRenderer(decorators=decorators)

    assert isinstance(renderer.decorators, list)
    assert len(renderer.decorators) == expected_len


def reload_json_and_base_modules() -> ModuleType:
    """
    Reload `internal.json` and `openapi.renderers.base`
        modules to reset their state.
    """  # noqa: D205
    sys.modules.pop(JSON_MODULE, None)
    sys.modules.pop(BASE_MODULE, None)
    return importlib.import_module(BASE_MODULE)


def test_prefers_msgspec_when_available(monkeypatch: MonkeyPatch) -> None:
    """Ensure that `json_serializer` prefers `msgspec`."""
    fake_msgspec = cast(Any, ModuleType('msgspec'))
    fake_msgspec.json = SimpleNamespace(
        encode=lambda schema: b'{"ok":true}',
    )

    monkeypatch.setitem(sys.modules, 'msgspec', fake_msgspec)

    base_module = reload_json_and_base_modules()

    assert base_module.json_serializer({'x': 1}) == '{"ok":true}'


def test_falls_back_to_stdlib_json(monkeypatch: MonkeyPatch) -> None:
    """
    Ensure `json_serializer` falls back to
        stdlib `json` if `msgspec` is unavailable.
    """  # noqa: D205
    monkeypatch.setitem(sys.modules, 'msgspec', None)

    import json as std_json  # noqa: PLC0415

    monkeypatch.setattr(
        std_json,
        'dumps',
        lambda schema: '{"fallback":true}',
    )

    base_module = reload_json_and_base_modules()

    assert base_module.json_serializer({'x': 1}) == '{"fallback":true}'
