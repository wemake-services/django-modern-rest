from collections.abc import Iterator
from typing import Final

import pytest
from django.conf import LazySettings
from django.urls import URLPattern

from django_modern_rest import Router
from django_modern_rest.openapi import OpenAPIConfig, openapi_spec
from django_modern_rest.openapi.renderers import (
    JsonRenderer,
    RedocRenderer,
    ScalarRenderer,
    SwaggerRenderer,
)
from django_modern_rest.settings import clear_settings_cache

_TEST_CONFIG: Final = OpenAPIConfig(title='Test API', version='1.0.0')


@pytest.fixture
def _clear_cache() -> Iterator[None]:
    """Clear settings cache before and after test."""
    clear_settings_cache()
    yield
    clear_settings_cache()


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

    pattern_names = [pattern.name for pattern in urlpatterns]
    assert 'json' in pattern_names
    assert 'redoc' in pattern_names
    assert 'scalar' in pattern_names
    assert 'swagger' in pattern_names


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


@pytest.mark.usefixtures('_clear_cache')
def test_with_none_config_uses_default() -> None:
    """Ensure that `None` config triggers default config loading."""
    urlpatterns, app_name, namespace = openapi_spec(
        router=Router([]),
        renderers=[JsonRenderer()],
    )

    assert isinstance(urlpatterns, list)
    assert len(urlpatterns) == 1
    assert app_name == 'openapi'
    assert namespace == 'docs'


@pytest.mark.usefixtures('_clear_cache')
def test_default_config_raises_when_wrong_type(
    settings: LazySettings,
) -> None:
    """Ensure that `TypeError` is raised when config is not `OpenAPIConfig`."""
    settings.DMR_SETTINGS = {
        'json_serialize': 'django_modern_rest.internal.json.serialize',
    }

    with pytest.raises(
        TypeError,
        match='OpenAPI config is not set',
    ):
        openapi_spec(
            router=Router([]),
            renderers=[JsonRenderer()],
        )


@pytest.mark.usefixtures('_clear_cache')
def test_default_config_raises_when_missing(settings: LazySettings) -> None:
    """Ensure that `TypeError` is raised when config key is missing."""
    settings.DMR_SETTINGS = {
        'json_serialize': 'django_modern_rest.internal.json.serialize',
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
