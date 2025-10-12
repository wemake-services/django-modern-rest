import abc
from typing import ClassVar, final, override

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.routing import Router


class BaseRenderer(abc.ABC):
    """Base renderer for OpenAPI."""

    @abc.abstractmethod
    def render(
        self,
        request: HttpRequest,
        config: OpenAPIConfig,
    ) -> HttpResponse:
        """Render the router and config to an HTTP response."""
        raise NotImplementedError


@final
class SwaggerRenderer(BaseRenderer):
    """Renderer for Swagger."""

    template_name: ClassVar[str] = 'modern_rest/swagger.html'

    @override
    def render(
        self,
        request: HttpRequest,
        config: OpenAPIConfig,
    ) -> HttpResponse:
        """Render the Swagger schema."""
        return render(
            request,
            self.template_name,
            context={'title': config.title},
        )


# TODO: add ReDoc renderer
# TODO: add OpenAPISchemaView
# TODO: add schema path customization
# TODO: extend OpenAPIConfig
# TODO: add CDN loads for ReDoc and Swagger
