from typing import ClassVar

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dmr.openapi.views.base import OpenAPIView


class RedocView(OpenAPIView):
    """
    View for rendering the OpenAPI schema with Redoc.

    Renders an interactive HTML page that allows exploring the
    :class:`~dmr.openapi.objects.OpenAPI` specification using Redoc
    components.

    Attributes:
        content_type: Content type of the rendered response. Defaults to
            ``"text/html"``.
        template_name: Template used to render the Redoc page.
    """

    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'dmr/redoc.html'

    def get(self, request: 'HttpRequest') -> 'HttpResponse':
        """Render the OpenAPI schema using Redoc template."""
        return render(
            request,
            self.template_name,
            context={
                'title': self.schema.info.title,
                'schema': self.dumps(self.schema.convert()),
            },
            content_type=self.content_type,
        )
