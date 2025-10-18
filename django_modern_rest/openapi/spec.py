from collections.abc import Sequence

from django.urls import URLPattern, path

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.renderers import BaseRenderer
from django_modern_rest.openapi.views import OpenAPIView
from django_modern_rest.routing import Router
from django_modern_rest.types import Empty, EmptyObj


def openapi_spec(
    router: Router,
    renderers: Sequence[BaseRenderer],
    config: OpenAPIConfig | Empty = EmptyObj,
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
            "Empty renderers sequence provided to 'openapi_spec()'. "
            'At least one renderer must be specified to '
            'render the API documentation.',
        )

    if isinstance(config, Empty):
        config = _default_config()

    # TODO: temporary schema without content
    schema = {'openapi': '3.1.0'}

    urlpatterns = [
        path(
            renderer.path,
            OpenAPIView.as_view(renderer=renderer, schema=schema),
            name=renderer.name,
        )
        for renderer in renderers
    ]
    return (urlpatterns, app_name, namespace)


def _default_config() -> OpenAPIConfig:
    from django_modern_rest.settings import (  # noqa: PLC0415
        DMR_OPENAPI_CONFIG_KEY,
        resolve_defaults,
    )

    config = resolve_defaults().get(DMR_OPENAPI_CONFIG_KEY)
    if not isinstance(config, OpenAPIConfig):
        raise TypeError(
            'OpenAPI config is not set. Please set the '
            "'DMR_OPENAPI_CONFIG' setting.",
        )
    return config
