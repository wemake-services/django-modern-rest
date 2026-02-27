from typing import TYPE_CHECKING, ClassVar

from django.shortcuts import render

from dmr.openapi.views.base import OpenAPIView

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class SwaggerView(OpenAPIView):
    """
    View for rendering the OpenAPI schema with Swagger UI.

    Renders an interactive HTML page that allows exploring the
    :class:`~dmr.openapi.objects.OpenAPI` specification using Swagger UI
    components.

    Attributes:
        content_type: Content type of the rendered response. Defaults to
            ``"text/html"``.
        template_name: Template used to render the Swagger UI page.
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
