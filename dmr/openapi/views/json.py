from typing import ClassVar

from django.http import HttpRequest, HttpResponse

from dmr.openapi.views.base import OpenAPIView


class OpenAPIJsonView(OpenAPIView):
    """
    Renderer OpenAPI schema in JSON format.

    Provides JSON representation of OpenAPI specification suitable for
    API documentation tools and client code generation.
    """

    content_type: ClassVar[str] = 'application/json'

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema as JSON response."""
        return HttpResponse(
            content=self.serializer(self.converted_schema),
            content_type=self.content_type,
        )
