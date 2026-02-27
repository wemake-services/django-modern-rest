from collections.abc import Callable
from typing import Any, ClassVar, final

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from typing_extensions import override

from dmr.openapi.objects.openapi import ConvertedSchema
from dmr.openapi.renderers import BaseRenderer


@final
@method_decorator(
    ensure_csrf_cookie,  # pyrefly: ignore[bad-argument-type]
    name='dispatch',
)
class OpenAPIView(View):
    """
    View for rendering OpenAPI schema documentation.

    This view handles rendering of OpenAPI specifications using
    different renderers (JSON, Swagger UI, etc.).

    The view only supports ``GET`` requests and delegates actual rendering
    to a `BaseRenderer` instance provided via `as_view`.
    """

    # Hack for preventing parent `as_view()` attributes validating
    renderer: ClassVar[BaseRenderer | None] = None
    schema: ClassVar[ConvertedSchema | None] = None

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handle `GET` request and render the OpenAPI schema."""
        if not isinstance(self.renderer, BaseRenderer):
            raise TypeError("Renderer must be a 'BaseRenderer' instance.")

        # for mypy: it must be set
        assert self.schema is not None  # noqa: S101
        return self.renderer.render(request, self.schema)

    @override
    @classmethod
    def as_view(  # type: ignore[override]
        cls,
        renderer: BaseRenderer,
        schema: ConvertedSchema,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Create a view callable with OpenAPI configuration.

        This method extends Django's base `as_view()` to accept
        and configure OpenAPI-specific parameters before creating
        the view callable.
        """
        return super().as_view(renderer=renderer, schema=schema, **initkwargs)
