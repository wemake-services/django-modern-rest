from typing import Any

from django.http import HttpRequest, HttpResponse
from django.views import View

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.renderers import BaseRenderer
from django_modern_rest.routing import Router
from django_modern_rest.settings import DMR_OPENAPI_CONFIG_KEY, resolve_defaults


class OpenAPIView(View):
    """View for OpenAPI."""

    router: Router = None  # type: ignore[assignment]
    renderer: BaseRenderer = None  # type: ignore[assignment]
    config: OpenAPIConfig = None  # type: ignore[assignment]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize OpenAPIView."""
        super().__init__(**kwargs)
        if getattr(self, 'router', None) is None:
            raise ValueError(
                "OpenAPIView requires either a definition of 'router'",
            )
        if getattr(self, 'renderer', None) is None:
            raise ValueError(
                "OpenAPIView requires either a definition of 'renderer'",
            )
        if getattr(self, 'config', None) is None:
            self.config = resolve_defaults()[DMR_OPENAPI_CONFIG_KEY]

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema."""
        return self.renderer.render(request, self.router, self.config)
