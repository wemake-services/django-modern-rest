from collections.abc import Callable
from typing import Any, ClassVar, final

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.views import View
from typing_extensions import override

from django_modern_rest.openapi import BaseRenderer
from django_modern_rest.openapi.generator import OpenAPISchema
from django_modern_rest.types import Empty, EmptyObj


@final
class OpenAPIView(View):
    """View for OpenAPI."""

    # Hack for preventing parent `as_view` from validating the attributes
    renderer: ClassVar[BaseRenderer | Empty] = EmptyObj
    schema: ClassVar[OpenAPISchema | Empty] = EmptyObj

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the OpenAPI schema."""
        if not isinstance(self.renderer, BaseRenderer):
            raise TypeError("Renderer must be a 'BaseRenderer' instance.")

        return self.renderer.render(request, self.schema)  # type: ignore[arg-type]

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
        return super().as_view(renderer=renderer, schema=schema, **initkwargs)
