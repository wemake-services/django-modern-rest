from typing import ClassVar

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dmr.openapi.views.base import OpenAPIView
from dmr.settings import Settings, resolve_setting


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
        cdn_config = resolve_setting(Settings.openapi_static_cdn)

        return render(
            request,
            self.template_name,
            context={
                'title': self.schema.info.title,
                'schema': self.schema.convert(
                    skip_validation=self.skip_validation,
                ),
                'swagger_cdn': cdn_config.get('swagger'),
            },
            content_type=self.content_type,
        )
