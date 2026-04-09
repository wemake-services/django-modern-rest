from typing import ClassVar

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dmr.openapi.views.base import OpenAPIView
from dmr.settings import Settings, resolve_setting


class StoplightView(OpenAPIView):
    """
    View for rendering the OpenAPI schema with Stoplight.

    Renders an interactive HTML page that allows exploring the
    :class:`~dmr.openapi.objects.OpenAPI` specification using Stoplight
    API Reference.

    Attributes:
        content_type: Content type of the rendered response. Defaults to
            ``"text/html"``.
        template_name: Template used to render the Stoplight page.
    """

    content_type: ClassVar[str] = 'text/html'
    template_name: ClassVar[str] = 'dmr/stoplight.html'

    def get(self, request: 'HttpRequest') -> 'HttpResponse':
        """Render the OpenAPI schema using Stoplight template."""
        cdn_config = resolve_setting(Settings.openapi_static_cdn)

        return render(
            request,
            self.template_name,
            context={
                'title': self.schema.info.title,
                'schema': self.dumps(
                    self.schema.convert(skip_validation=self.skip_validation),
                ),
                'stoplight_cdn': cdn_config.get('stoplight'),
            },
            content_type=self.content_type,
        )
