from typing import TYPE_CHECKING, ClassVar

from django.shortcuts import render

from dmr.openapi.views.base import OpenAPIView

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class ScalarView(OpenAPIView):
    """
    View for rendering the OpenAPI schema with Scalar.

    Renders an interactive HTML page that allows exploring the
    :class:`~dmr.openapi.objects.OpenAPI` specification using Scalar
    API Reference.

    Attributes:
        content_type: Content type of the rendered response. Defaults to
            ``"text/html"``.
        template_name: Template used to render the Scalar page.
    """

    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'dmr/scalar.html'

    def get(self, request: 'HttpRequest') -> 'HttpResponse':
        """Render the OpenAPI schema using Scalar template."""
        return render(
            request,
            self.template_name,
            context={
                'title': self.schema.info.title,
                'schema': self.dumps(self.schema.convert()),
            },
            content_type=self.content_type,
        )
