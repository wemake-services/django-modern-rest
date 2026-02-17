from typing import ClassVar, final

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from typing_extensions import override

from dmr.openapi.converter import ConvertedSchema
from dmr.openapi.renderers.base import (
    BaseRenderer,
    SchemaSerializer,
    json_serializer,
)


@final
class ScalarRenderer(BaseRenderer):
    """
    Renderer for OpenAPI schema using Scalar.

    Provides interactive HTML interface for exploring OpenAPI specification
    using Scalar API Reference.
    """

    # TODO: implement local static loading
    default_path: ClassVar[str] = 'scalar/'
    default_name: ClassVar[str] = 'scalar'
    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'dmr/scalar.html'
    serializer: SchemaSerializer = staticmethod(json_serializer)  # noqa: WPS421

    @override
    def render(
        self,
        request: HttpRequest,
        schema: ConvertedSchema,
    ) -> HttpResponse:
        """Render the OpenAPI schema using Scalar template."""
        return render(
            request,
            self.template_name,
            context={
                'title': schema['info']['title'],
                'schema': self.serializer(schema),
            },
            content_type=self.content_type,
        )
