from typing import ClassVar

from django.http import HttpRequest, HttpResponse

from dmr.internal.yaml import yaml_dumps
from dmr.openapi.views.base import OpenAPIView


class OpenAPIYamlView(OpenAPIView):
    """
    View for returning the OpenAPI schema as YAML.

    This view mirrors :class:`~dmr.openapi.views.json.OpenAPIJsonView`,
    but renders the converted schema using ``msgspec.yaml``.
    """

    content_type: ClassVar[str] = 'application/yaml'
    dumps = staticmethod(yaml_dumps)

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema as YAML response."""
        return HttpResponse(
            content=self.dumps(self.schema.convert()),
            content_type=self.content_type,
        )
