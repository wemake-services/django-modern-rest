from collections.abc import Callable
from typing import Any, ClassVar

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.views import View
from typing_extensions import override

from django_modern_rest.openapi import BaseRenderer
from django_modern_rest.openapi.schema import OpenAPISchema


class OpenAPIView(View):
    """View for OpenAPI."""

    renderer: ClassVar[BaseRenderer]
    schema: ClassVar[OpenAPISchema]

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema."""
        return self.renderer.render(request, self.schema)

    @override
    @classmethod
    def as_view(  # type: ignore[override]
        cls,
        renderer: BaseRenderer,
        schema: OpenAPISchema,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Extend the base view to include OpenAPI configuration.

        This method extends Django's base 'as_view()' to handle OpenAPI
        parameters.
        """
        # We need to set these attributes on the class before calling
        # `super().as_view()` because Django's base `as_view()` method
        # validates that any initkwargs correspond to existing class attributes.
        # By setting these attributes first, we ensure that the parameters
        # can be passed as initkwargs to the parent method without
        # causing validation errors.
        cls.renderer = renderer
        cls.schema = schema

        return super().as_view(
            renderer=renderer,
            schema=schema,
            **initkwargs,
        )
