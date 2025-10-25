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
class RedocRenderer(BaseRenderer):
    """
    Renderer for OpenAPI schema using Redoc.

    Provides interactive HTML interface for exploring OpenAPI specification
    using Redoc components.
    """

    default_path: ClassVar[str] = 'redoc/'
    default_name: ClassVar[str] = 'redoc'
    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'django_modern_rest/redoc.html'
    serializer: SchemaSerialier = staticmethod(json_serializer)  # noqa: WPS421

    @override
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the OpenAPI schema using Redoc template."""
        return render(
            request,
            self.template_name,
            context={
                'title': schema['info']['title'],
                'schema': self.serializer(schema),
            },
            content_type=self.content_type,
        )
