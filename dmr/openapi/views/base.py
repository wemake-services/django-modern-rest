from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias

from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from typing_extensions import override

from dmr.internal.json import json_dumps

if TYPE_CHECKING:
    from django.http import HttpResponseBase

    from dmr.openapi.objects import OpenAPI
    from dmr.openapi.objects.openapi import ConvertedSchema

DumpedSchema: TypeAlias = str
SchemaDumper: TypeAlias = Callable[['ConvertedSchema'], DumpedSchema]


@method_decorator(
    ensure_csrf_cookie,  # pyrefly: ignore[bad-argument-type]
    name='dispatch',
)
class OpenAPIView(View):
    """
    Base view for serving an OpenAPI schema.

    This view extends Django's :class:`django.views.View` to accept an
    :class:`~dmr.openapi.objects.OpenAPI` instance via :meth:`as_view`.
    The passed schema is stored on the view class and can be rendered in
    any concrete subclass (for example, as JSON or YAML).

    Attributes:
        dumps: Callable that converts a converted OpenAPI schema into a string.
            Defaults to :func:`dmr.internal.json.json_dumps`.
        schema: The OpenAPI schema associated with this view. Set when
            :meth:`as_view` is called.
    """

    # Public API:
    dumps: SchemaDumper = staticmethod(json_dumps)  # noqa: WPS421
    schema: ClassVar['OpenAPI']

    @override
    @classmethod
    def as_view(  # type: ignore[override]
        cls,
        schema: 'OpenAPI',
        **initkwargs: Any,
    ) -> Callable[..., 'HttpResponseBase']:
        """
        Create a view function bound to the given OpenAPI schema.

        Extends Django's :meth:`django.views.View.as_view` to accept an
        :class:`~dmr.openapi.objects.OpenAPI` instance, store it on the
        view class, and then return the configured view callable.
        """
        cls.schema = schema
        return super().as_view(**initkwargs)
