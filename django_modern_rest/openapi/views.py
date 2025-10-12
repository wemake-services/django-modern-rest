from collections.abc import Callable
from typing import Any, cast, override

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.views import View

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.renderers import BaseRenderer
from django_modern_rest.routing import Router
from django_modern_rest.settings import DMR_OPENAPI_CONFIG_KEY, resolve_defaults


class OpenAPIView(View):
    """View for OpenAPI."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema."""
        return cast(
            HttpResponse,
            self.renderer.render(request, self.router, self.config),  # type: ignore[attr-defined]
        )

    @override
    @classmethod
    def as_view(  # type: ignore[override]
        cls,
        router: Router,
        renderer: BaseRenderer,
        config: OpenAPIConfig | None = None,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Extend the base view to include OpenAPI configuration.

        This method extends Django's base 'as_view()' to handle OpenAPI
        parameters by setting them as class attributes rather than passing
        them through initkwargs.
        """
        if config is None:
            config = cls._default_config()

        cls.router = router
        cls.renderer = renderer
        cls.config = config

        return super().as_view(**initkwargs)

    @classmethod
    def _default_config(cls) -> OpenAPIConfig:
        config = resolve_defaults().get(DMR_OPENAPI_CONFIG_KEY)
        if not isinstance(config, OpenAPIConfig):
            raise TypeError(
                'OpenAPI config is not set. Please set the '
                "'DMR_OPENAPI_CONFIG_KEY' setting.",
            )
        return config
