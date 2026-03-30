from typing import ClassVar

from django.http import HttpRequest, HttpResponse

from dmr.openapi.views.base import OpenAPIView
from dmr.plugins.msgspec.yaml import yaml_dumps


class OpenAPIYamlView(OpenAPIView):
    """
    View for returning the OpenAPI schema as YAML.

    This view mirrors :class:`~dmr.openapi.views.json.OpenAPIJsonView`,
    but renders the converted schema using ``msgspec.yaml``.
    Produces a YAML representation of the :class:`~dmr.openapi.objects.OpenAPI`
    specification that can be used by API documentation tools
    and client code generators.
    """

    content_type: ClassVar[str] = 'application/yaml'

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema as YAML response."""
        return HttpResponse(
            content=yaml_dumps(self.schema.convert()),
            content_type=self.content_type,
        )
