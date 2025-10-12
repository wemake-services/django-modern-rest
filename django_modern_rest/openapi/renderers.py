import abc
from typing import ClassVar, final

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from typing_extensions import override

from django_modern_rest.openapi.config import OpenAPIConfig


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
