from typing import Any

from django.http import HttpRequest, HttpResponse
from django.views import View

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.renderers import BaseRenderer
from django_modern_rest.routing import Router
from django_modern_rest.settings import DMR_OPENAPI_CONFIG_KEY, resolve_defaults


class OpenAPIView(View):
    """View for OpenAPI."""

    router: Router | None = None
    renderer: type[BaseRenderer] | None = None
    config: OpenAPIConfig | None = None

    def __init__(self, **kwargs: Any) -> None:
        """Initialize OpenAPIView."""
        super().__init__(**kwargs)
        if not self.router:
            raise ValueError(
                'Router is not set for `OpenAPIView` instance. '
                'Please assign a `Router` instance to the `router`'
                'attribute before using this view.',
            )
        if not self.renderer:
            raise ValueError(
                'Renderer is not set for `OpenAPIView` instance. '
                'Please assign a `BaseRenderer` subclass to the `renderer`'
                'attribute before using this view.',
            )
        if not self.config:
            self.config = resolve_defaults()[DMR_OPENAPI_CONFIG_KEY]

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema."""
        return self.renderer.render(request, self.router, self.config)
