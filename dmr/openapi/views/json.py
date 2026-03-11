from typing import ClassVar

from django.http import HttpRequest, HttpResponse

from dmr.openapi.views.base import OpenAPIView


class OpenAPIJsonView(OpenAPIView):
    """
    View for returning the OpenAPI schema as JSON.

    Produces a JSON representation of the :class:`~dmr.openapi.objects.OpenAPI`
    specification that can be used by API documentation tools
    and client code generators.

    Attributes:
        content_type: Content type of the rendered response. Defaults to
            ``"application/json"``.

    """

    content_type: ClassVar[str] = 'application/json'

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema as JSON response."""
        return HttpResponse(
            content=self.dumps(self.schema.convert()),
            content_type=self.content_type,
        )
