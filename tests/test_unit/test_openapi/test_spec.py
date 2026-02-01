from typing import Final

import pytest
from django.conf import LazySettings
from django.urls import URLPattern
from django.views.decorators.csrf import csrf_exempt

from django_modern_rest.openapi import OpenAPIConfig, openapi_spec
from django_modern_rest.openapi.renderers import (
    JsonRenderer,
    RedocRenderer,
    ScalarRenderer,
    SwaggerRenderer,
)
from django_modern_rest.routing import Router

_TEST_CONFIG: Final = OpenAPIConfig(title='Test API', version='1.0.0')


def test_returns_correct_structure() -> None:
    """Ensure that `openapi_spec` returns correct tuple structure."""
    urlpatterns, app_name, namespace = openapi_spec(
        router=Router([]),  # noqa: WPS204
        renderers=[JsonRenderer()],
        config=_TEST_CONFIG,
    )

    assert isinstance(urlpatterns, list)
    assert len(urlpatterns) == 1
    assert isinstance(urlpatterns[0], URLPattern)
    assert app_name == 'openapi'
    assert namespace == 'docs'


def test_creates_pattern_per_renderer() -> None:
    """Ensure that each renderer creates a URL pattern."""
    router = Router([])
    renderers = [JsonRenderer(), SwaggerRenderer()]

    urlpatterns, _, _ = openapi_spec(
        router=router,
        renderers=renderers,
        config=_TEST_CONFIG,
    )

    assert len(urlpatterns) == len(renderers)
    assert all(isinstance(pattern, URLPattern) for pattern in urlpatterns)


def test_pattern_names_match_renderers() -> None:
    """Ensure that URL pattern names match renderer names."""
    urlpatterns, _, _ = openapi_spec(
        router=Router([]),
        renderers=[
            JsonRenderer(),
            RedocRenderer(),
            ScalarRenderer(),
            SwaggerRenderer(),
        ],
        config=_TEST_CONFIG,
    )

    renderer_names = {'json', 'redoc', 'scalar', 'swagger'}
    assert {pattern.name for pattern in urlpatterns} == renderer_names


@pytest.mark.parametrize(
    ('app_name', 'namespace'),
    [
        ('openapi', 'docs'),
        ('custom_app', 'custom_namespace'),
        ('api', 'v1'),
    ],
)
def test_custom_app_and_namespace(
    *,
    app_name: str,
    namespace: str,
) -> None:
    """Ensure that custom `app_name` and `namespace` are returned."""
    _, returned_app_name, returned_namespace = openapi_spec(
        router=Router([]),
        renderers=[JsonRenderer()],
        config=_TEST_CONFIG,
        app_name=app_name,
        namespace=namespace,
    )

    assert returned_app_name == app_name
    assert returned_namespace == namespace


def test_with_none_config_uses_default(dmr_clean_settings: None) -> None:
    """Ensure that `None` config triggers default config loading."""
    urlpatterns, app_name, namespace = openapi_spec(
        router=Router([]),
        renderers=[JsonRenderer()],
    )

    assert isinstance(urlpatterns, list)
    assert len(urlpatterns) == 1
    assert app_name == 'openapi'
    assert namespace == 'docs'


def test_default_config_raises_when_wrong_type(
    dmr_clean_settings: None,
    settings: LazySettings,
) -> None:
    """Ensure that `TypeError` is raised when config is not `OpenAPIConfig`."""
    settings.DMR_SETTINGS = {
        'openapi_config': 'not-an-object',
    }

    with pytest.raises(
        TypeError,
        match='OpenAPI config is not set',
    ):
        openapi_spec(
            router=Router([]),
            renderers=[JsonRenderer()],
        )


def test_empty_renderers_list() -> None:
    """Ensure that empty renderers list creates no URL patterns."""
    with pytest.raises(
        ValueError,
        match='At least one renderer must be specified',
    ):
        openapi_spec(
            router=Router([]),
            renderers=[],
            config=_TEST_CONFIG,
        )


def test_decorated_view_with_csrf_exempt() -> None:
    """Ensure that csrf_exempt decorator is applied to view."""
    urlpatterns, _, _ = openapi_spec(
        router=Router([]),
        renderers=[JsonRenderer(decorators=[csrf_exempt])],
        config=_TEST_CONFIG,
    )

    assert urlpatterns[0].callback.csrf_exempt is True  # type: ignore[attr-defined]
