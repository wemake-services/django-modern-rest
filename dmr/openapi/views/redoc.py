from typing import TYPE_CHECKING, ClassVar

from django.shortcuts import render

from dmr.openapi.views.base import OpenAPIView

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class RedocView(OpenAPIView):
    """
    Renderer OpenAPI schema using Redoc.

    Provides interactive HTML interface for exploring OpenAPI specification
    using Redoc components.
    """

    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'dmr/redoc.html'

    def get(self, request: 'HttpRequest') -> 'HttpResponse':
        """Render the OpenAPI schema using Redoc template."""
        return render(
            request,
            self.template_name,
            context={
                'title': self.converted_schema['info']['title'],
                'schema': self.serializer(self.converted_schema),
            },
            content_type=self.content_type,
        )
