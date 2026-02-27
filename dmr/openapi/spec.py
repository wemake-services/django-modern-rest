from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.urls import URLPattern

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.builder import OpenApiBuilder
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.objects.openapi import OpenAPI
from dmr.openapi.views import OpenAPIView
from dmr.routing import path

if TYPE_CHECKING:
    from dmr.openapi.renderers import BaseRenderer
    from dmr.routing import Router


def openapi_spec(
    router: 'Router',
    renderers: 'Sequence[BaseRenderer]',
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

    schema = build_schema(router, config=config).convert()

    urlpatterns: list[URLPattern] = []
    for renderer in renderers:
        view = OpenAPIView.as_view(renderer=renderer, schema=schema)
        if renderer.decorators:
            for decorator in renderer.decorators:
                view = decorator(view)

        urlpatterns.append(path(renderer.path, view, name=renderer.name))

    return (urlpatterns, app_name, namespace)


def build_schema(
    router: 'Router',
    *,
    config: OpenAPIConfig | None = None,
) -> OpenAPI:
    """
    Build OpenAPI schema.

    Parameters:
        router: Router that contains all API endpoints and all controllers.
        config: Optional configuration of OpenAPI metadata.
            Can be ``None``, in this case we fetch OpenAPI config from settings.

    """
    context = OpenAPIContext(config=config or _default_config())
    return OpenApiBuilder(context)(router)


def _default_config() -> OpenAPIConfig:
    from dmr.settings import (  # noqa: PLC0415
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
