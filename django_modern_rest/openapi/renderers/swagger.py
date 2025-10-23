from typing import ClassVar, final

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from typing_extensions import override

from django_modern_rest.openapi.converter import ConvertedSchema
from django_modern_rest.openapi.renderers.base import (
    BaseRenderer,
    SchemaSerialier,
    json_serializer,
)


@final
class SwaggerRenderer(BaseRenderer):
    """
    Renderer for OpenAPI schema using Swagger UI.

    Provides interactive HTML interface for exploring OpenAPI specification
    using Swagger UI components.
    """

    # TODO: implement cdn static loading
    default_path: ClassVar[str] = 'swagger/'
    default_name: ClassVar[str] = 'swagger'
    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'django_modern_rest/swagger.html'
    serializer: SchemaSerialier = staticmethod(json_serializer)  # noqa: WPS421

    @override
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the OpenAPI schema using Swagger UI template."""
        return render(
            request,
            self.template_name,
            context={
                'title': schema['info']['title'],
                'schema': self.serializer(schema),
            },
            content_type=self.content_type,
        )
