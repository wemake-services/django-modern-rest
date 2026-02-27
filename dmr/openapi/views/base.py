from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, override

from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from dmr.internal.json import json_dumps

if TYPE_CHECKING:
    from django.http import HttpResponseBase

    from dmr.internal.json import SerializedSchema
    from dmr.openapi.objects import OpenAPI
    from dmr.openapi.objects.openapi import ConvertedSchema

SchemaSerializer: TypeAlias = Callable[['ConvertedSchema'], 'SerializedSchema']


@method_decorator(
    ensure_csrf_cookie,  # pyrefly: ignore[bad-argument-type]
    name='dispatch',
)
class OpenAPIView(View):
    """
    Base view for serving an OpenAPI schema.

    Extends Django's ``View`` to accept an ``OpenAPI`` object via ``as_view()``.
    The provided schema is converted using ``schema_converter_cls``
    and stored on the view instance so that concrete subclasses can
    render it in their preferred format.
    """

    # Public API:
    serializer: SchemaSerializer = staticmethod(json_dumps)  # noqa: WPS421
    schema: ClassVar['OpenAPI']

    @override
    @classmethod
    def as_view(  # type: ignore[override]
        cls,
        schema: 'OpenAPI',
        **initkwargs: Any,
    ) -> Callable[..., 'HttpResponseBase']:
        """
        Create a view callable with OpenAPI schema.

        This method extends Django's base ``as_view()`` to accept
        and configure OpenAPI schema parameter before creating
        the view callable.
        """
        cls.schema = schema
        return super().as_view(**initkwargs)
