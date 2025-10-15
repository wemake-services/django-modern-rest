import abc
from typing import TYPE_CHECKING, ClassVar, final

import msgspec
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from typing_extensions import override

if TYPE_CHECKING:
    from django_modern_rest.openapi.generator import OpenAPISchema


class BaseRenderer(abc.ABC):
    """Base renderer for OpenAPI."""

    def __init__(self, path: str, name: str) -> None:
        self.path = path
        self.name = name

    @abc.abstractmethod
    def render(
        self,
        request: HttpRequest,
        schema: 'OpenAPISchema',
    ) -> HttpResponse:
        """Render the router and config to an HTTP response."""
        raise NotImplementedError

    # TODO: supports different decoding options
    def to_json(self, schema: 'OpenAPISchema') -> str:
        return msgspec.json.encode(schema).decode('utf-8')


@final
class JsonRenderer(BaseRenderer):
    """Renderer for JSON."""

    content_type: ClassVar[str] = 'application/json'

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
        schema: 'OpenAPISchema',
    ) -> HttpResponse:
        """Render the JSON schema."""
        return HttpResponse(
            content=self.to_json(schema),
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
        schema: 'OpenAPISchema',
    ) -> HttpResponse:
        """Render the Swagger schema."""
        return render(
            request,
            self.template_name,
            context={'spec': self.to_json(schema)},
            content_type=self.content_type,
        )


# TODO: add ReDoc renderer
# TODO: add CDN loads for ReDoc and Swagger
