from collections.abc import Callable
from typing import Any, ClassVar

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.views import View
from typing_extensions import override

from django_modern_rest.openapi import BaseRenderer, OpenAPIConfig
from django_modern_rest.routing import Router


class OpenAPIView(View):
    """View for OpenAPI."""

    router: ClassVar[Router]
    renderer: ClassVar[BaseRenderer]
    config: ClassVar[OpenAPIConfig]

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema."""
        return self.renderer.render(request, self.config)

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
        # Local import to avoid circular import
        from django_modern_rest.settings import (
            DMR_OPENAPI_CONFIG_KEY,
            resolve_defaults,
        )

        config = resolve_defaults().get(DMR_OPENAPI_CONFIG_KEY)
        if not isinstance(config, OpenAPIConfig):
            raise TypeError(
                'OpenAPI config is not set. Please set the '
                "'DMR_OPENAPI_CONFIG_KEY' setting.",
            )
        return config
