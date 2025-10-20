import abc
from typing import ClassVar, final

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from typing_extensions import override

from django_modern_rest.openapi.converter import ConvertedSchema


class BaseRenderer:
    """Base renderer for OpenAPI."""

    def __init__(self, path: str, name: str) -> None:
        """Base constructor."""
        # TODO: why do we need this?
        self.path = path
        self.name = name

    @abc.abstractmethod
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the router and config to an HTTP response."""
        raise NotImplementedError

    # TODO: support different decoding options
    def serialize(self, schema: ConvertedSchema) -> str:
        """Convert schema to json string."""
        from django_modern_rest.settings import (  # noqa: PLC0415
            DMR_SERIALIZE_KEY,
            resolve_setting,
        )

        serialize = resolve_setting(DMR_SERIALIZE_KEY, import_string=True)
        return serialize(schema).decode('utf-8')  # type: ignore[no-any-return]


@final
class JsonRenderer(BaseRenderer):  # TODO: a dataclass?
    """Renderer for JSON."""

    content_type: ClassVar[str] = 'application/json'

    def __init__(
        self,
        path: str = 'openapi.json/',
        name: str = 'json',
    ) -> None:
        """Create JsonRenderer."""
        super().__init__(path, name)

    @override
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the JSON schema."""
        return HttpResponse(
            content=self.serialize(schema),
            content_type=self.content_type,
        )


@final
class SwaggerRenderer(BaseRenderer):
    """Renderer for Swagger."""

    template_name: ClassVar[str] = 'django_modern_rest/swagger.html'
    content_type: ClassVar[str] = 'text/html'

    def __init__(
        self,
        # TODO(@kondratevdev): why do we need `path` and `name`?
        path: str = 'swagger/',
        name: str = 'swagger',
    ) -> None:
        """Create Swagger renderer."""
        super().__init__(path=path, name=name)

    @override
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the Swagger schema."""
        return render(
            request,
            self.template_name,
            context={'spec': self.serialize(schema)},
            content_type=self.content_type,
        )


# TODO: add ReDoc renderer
# TODO: add CDN loads for ReDoc and Swagger
