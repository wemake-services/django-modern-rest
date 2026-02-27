from typing import ClassVar, final

from django.http import HttpRequest, HttpResponse
from typing_extensions import override

from dmr.openapi.objects.openapi import ConvertedSchema
from dmr.openapi.renderers.base import (
    BaseRenderer,
    SchemaSerializer,
    json_serializer,
)


@final
class JsonRenderer(BaseRenderer):
    """
    Renderer for OpenAPI schema in JSON format.

    Provides JSON representation of OpenAPI specification suitable for
    API documentation tools and client code generation.
    """

    default_path: ClassVar[str] = 'openapi.json/'
    default_name: ClassVar[str] = 'json'
    content_type: ClassVar[str] = 'application/json'
    serializer: SchemaSerializer = staticmethod(json_serializer)  # noqa: WPS421

    @override
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the OpenAPI schema as JSON response."""
        return HttpResponse(
            content=self.serializer(schema),
            content_type=self.content_type,
        )
