import abc
from typing import ClassVar, final

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from typing_extensions import override

from django_modern_rest.openapi.config import OpenAPIConfig


class BaseRenderer(abc.ABC):
    """Base renderer for OpenAPI."""

    def __init__(self, path: str, name: str) -> None:
        self.path = path
        self.name = name

    @abc.abstractmethod
    def render(
        self,
        request: HttpRequest,
        config: OpenAPIConfig,
    ) -> HttpResponse:
        """Render the router and config to an HTTP response."""
        raise NotImplementedError


@final
class JsonRenderer(BaseRenderer):
    """Renderer for JSON."""

    content_type: ClassVar[str] = 'application/vnd.oai.openapi+json'

    def __init__(
        self,
        path: str = 'openapi.json/',
        name: str = 'json',
    ) -> None:
        self.path = path
        self.name = name

    @override
    def render(
        self,
        request: HttpRequest,
        config: OpenAPIConfig,
    ) -> HttpResponse:
        """Render the JSON schema."""
        # TODO: Render the OpenAPI JSON schema.
        return JsonResponse(
            data={'title': config.title},
            content_type=self.content_type,
        )


@final
class SwaggerRenderer(BaseRenderer):
    """Renderer for Swagger."""

    template_name: ClassVar[str] = 'django_modern_rest/swagger.html'
    content_type: ClassVar[str] = 'text/html'

    def __init__(
        self,
        path: str = 'swagger/',
        name: str = 'swagger',
    ) -> None:
        self.path = path
        self.name = name

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
            content_type=self.content_type,
        )


# TODO: add ReDoc renderer
# TODO: add OpenAPISchemaView
# TODO: add schema path customization
# TODO: extend OpenAPIConfig
# TODO: add CDN loads for ReDoc and Swagger
