from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, override

from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from dmr.internal.json import json_dumps
from dmr.openapi.converter import SchemaConverter

if TYPE_CHECKING:
    from django.http import HttpResponseBase

    from dmr.internal.json import SerializedSchema
    from dmr.openapi.converter import ConvertedSchema
    from dmr.openapi.objects import OpenAPI


SchemaSerializer: TypeAlias = Callable[['ConvertedSchema'], 'SerializedSchema']


@method_decorator(
    ensure_csrf_cookie,  # pyrefly: ignore[bad-argument-type]
    name='dispatch',
)
class OpenAPIView(View):
    """
    Base view for serving an OpenAPI schema.

    Extends Django's ``View`` to accept an ``OpenAPI`` object via
    ``as_view()``. The schema is converted to ``ConvertedSchema`` during
    initialization using ``schema_converter_cls`` and stored on the
    instance for use in concrete renderers.
    """

    # Public API:
    schema_converter_cls: ClassVar[type[SchemaConverter]] = SchemaConverter
    serializer: SchemaSerializer = staticmethod(json_dumps)  # noqa: WPS421

    # Hack for preventing `as_view()` attributes validating
    schema: ClassVar['OpenAPI | None'] = None

    @override
    def __init__(self, **kwargs: Any) -> None:
        """Initialize the view and convert the provided OpenAPI schema."""
        super().__init__(**kwargs)
        self.converted_schema = self.schema_converter_cls.convert(self.schema)  # type: ignore[arg-type]

    @override
    @classmethod
    def as_view(  # type: ignore[override]
        cls,
        schema: 'OpenAPI',
        **initkwargs: Any,
    ) -> Callable[..., 'HttpResponseBase']:
        """
        Create a view callable with OpenAPI schema.

        This method extends Django's base `as_view()` to accept
        and configure OpenAPI schema parameter before creating
        the view callable.
        """
        return super().as_view(schema=schema, **initkwargs)
