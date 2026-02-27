from typing import TYPE_CHECKING, ClassVar

from django.shortcuts import render

from dmr.openapi.views.base import OpenAPIView

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class SwaggerView(OpenAPIView):
    """
    Renderer for ``OpenAPI`` schema using Swagger UI.

    Provides interactive HTML interface for exploring OpenAPI specification
    using Swagger UI components.
    """

    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'dmr/swagger.html'

    def get(self, request: 'HttpRequest') -> 'HttpResponse':
        """Render the OpenAPI schema using Swagger template."""
        return render(
            request,
            self.template_name,
            context={
                'title': self.schema.info.title,
                'schema': self.dumps(self.schema.convert()),
            },
            content_type=self.content_type,
        )
