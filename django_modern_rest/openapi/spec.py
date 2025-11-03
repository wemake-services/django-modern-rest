from collections.abc import Sequence

from django.urls import URLPattern

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.converter import (
    ConvertedSchema,
    SchemaConverter,
)
from django_modern_rest.openapi.core.builder import OpenApiBuilder
from django_modern_rest.openapi.core.context import OpenAPIContext
from django_modern_rest.openapi.renderers import BaseRenderer
from django_modern_rest.openapi.views import OpenAPIView
from django_modern_rest.routing import Router, path


def openapi_spec(
    router: Router,
    renderers: Sequence[BaseRenderer],
    config: OpenAPIConfig | None = None,
    app_name: str = 'openapi',
    namespace: str = 'docs',
) -> tuple[list[URLPattern], str, str]:
    """
    Generate OpenAPI specification for API documentation.

    Rendering OpenAPI documentation using the provided renderers.
    The function generates an OpenAPI schema from the router's endpoints
    and creates views for each renderer.
    """
    if len(renderers) == 0:
        raise ValueError(
            'Empty renderers sequence provided to `openapi_spec()`. '
            'At least one renderer must be specified to '
            'render the API documentation.',
        )

    schema = _build_schema(config or _default_config(), router)

    urlpatterns: list[URLPattern] = []
    for renderer in renderers:
        view = OpenAPIView.as_view(renderer=renderer, schema=schema)
        if renderer.decorators:
            for decorator in renderer.decorators:
                view = decorator(view)

        urlpatterns.append(path(renderer.path, view, name=renderer.name))

    return (urlpatterns, app_name, namespace)


def _default_config() -> OpenAPIConfig:
    from django_modern_rest.settings import (  # noqa: PLC0415
        Settings,
        resolve_setting,
    )

    config = resolve_setting(Settings.openapi_config)
    if not isinstance(config, OpenAPIConfig):
        raise TypeError(
            'OpenAPI config is not set. Please, set the '
            f'{str(Settings.openapi_config)!r} setting.',
        )
    return config


def _build_schema(config: OpenAPIConfig, router: Router) -> ConvertedSchema:
    # TODO: refactor
    context = OpenAPIContext(config=config)
    schema = OpenApiBuilder(context).build(router)
    return SchemaConverter.convert(schema)
