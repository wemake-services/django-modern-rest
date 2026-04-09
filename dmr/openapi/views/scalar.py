from typing import ClassVar

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dmr.openapi.views.base import OpenAPIView
from dmr.settings import Settings, resolve_setting


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
        cdn_config = resolve_setting(Settings.openapi_static_cdn)

        return render(
            request,
            self.template_name,
            context={
                'title': self.schema.info.title,
                'schema': (
                    self.schema.convert(skip_validation=self.skip_validation),
                ),
                'scalar_cdn': cdn_config.get('scalar'),
            },
            content_type=self.content_type,
        )
