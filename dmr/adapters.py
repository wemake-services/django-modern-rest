"""
Adapters that make plain Django views visible in the OpenAPI specification.

An adapted view is documented, not adopted: it keeps dispatching exactly
as it would under plain ``django.urls.path``. See :func:`adapt_django_view`.
"""

import dataclasses
from collections.abc import Mapping
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    NoReturn,
    TypeAlias,
    TypeVar,
    cast,
)

from django.views import View

from dmr.openapi.core.registry import ComponentRegistry
from dmr.openapi.objects import Components, PathItem
from dmr.openapi.objects.openapi import normalize_key

if TYPE_CHECKING:
    from django.urls import URLPattern

    from dmr.openapi.core.context import OpenAPIContext
    from dmr.routing import Router

_ViewT = TypeVar('_ViewT', bound=View)

RawPathItem: TypeAlias = Mapping[str, Any]
"""
Path item spelled the way it appears in an OpenAPI document.

.. versionadded:: 0.13.0

"""

RawComponents: TypeAlias = Mapping[str, Any]
"""
Reusable components spelled the way they appear in an OpenAPI document.

Maps a component category, such as ``responses``, to the components in it.

.. versionadded:: 0.13.0

"""

#: The only path item key that is not a valid python identifier.
_REF_KEY: Final = '$ref'

#: Contributable component categories, keyed by their document spelling.
_COMPONENT_FIELDS: Final = MappingProxyType({
    normalize_key(category): category
    for category in ComponentRegistry.categories
})


class _AdaptedView:
    """Reports a statically supplied description to the schema collector."""

    __slots__ = ()

    _openapi: ClassVar[PathItem]
    _openapi_components: ClassVar[Components | None]

    @classmethod
    def get_path_item(
        cls,
        path: str,
        pattern: 'URLPattern',
        context: 'OpenAPIContext',
        router: 'Router',
    ) -> PathItem:
        """Contribute the components, then report the path item."""
        if cls._openapi_components is not None:
            context.registries.component.contribute(cls._openapi_components)
        return cls._openapi


def adapt_django_view(
    view_class: type[_ViewT],
    *,
    openapi: 'PathItem | RawPathItem',
    components: 'Components | RawComponents | None' = None,
) -> type[_ViewT]:
    """
    Document a plain Django view in the generated OpenAPI specification.

    Returns a subclass of *view_class* that the schema collector can consume.
    Mount it in a :class:`~dmr.routing.Router` like any other view:

    .. code:: python

        >>> from django.http import HttpResponse
        >>> from django.urls import path
        >>> from django.views import View

        >>> from dmr.adapters import adapt_django_view
        >>> from dmr.openapi.objects import Operation, PathItem, Response
        >>> from dmr.routing import Router

        >>> class LegacyExportView(View):
        ...     def get(self, request):
        ...         return HttpResponse('id,name', content_type='text/csv')

        >>> LegacyExport = adapt_django_view(
        ...     LegacyExportView,
        ...     openapi=PathItem(
        ...         get=Operation(
        ...             summary='Export report as CSV',
        ...             responses={'200': Response(description='CSV payload')},
        ...         ),
        ...     ),
        ... )

        >>> router = Router('api/', [path('export/', LegacyExport.as_view())])

    The path item can also be a plain mapping, so a fragment of an existing
    specification can be pasted in without translating it into typed objects:

    .. code:: python

        >>> LegacyExport = adapt_django_view(
        ...     LegacyExportView,
        ...     openapi={
        ...         'get': {
        ...             'summary': 'Export report as CSV',
        ...             'responses': {'200': {'description': 'CSV payload'}},
        ...         },
        ...     },
        ... )

    A path item that references reusable components carries them in
    *components*, in the same two spellings. Only the categories a description
    can reference are accepted — ``schemas``, ``responses``, ``parameters``,
    ``examples`` and ``requestBodies``:

    .. code:: python

        >>> LegacyExport = adapt_django_view(
        ...     LegacyExportView,
        ...     openapi={
        ...         'get': {
        ...             'summary': 'Export report as CSV',
        ...             'responses': {
        ...                 '200': {'$ref': '#/components/responses/Csv'},
        ...             },
        ...         },
        ...     },
        ...     components={
        ...         'responses': {'Csv': {'description': 'CSV payload'}},
        ...     },
        ... )

    Any other category is rejected rather than dropped, in either spelling.

    Contributed components share one document with the schemas the framework
    generates from controllers, and a generated schema always wins a name
    clash, so give them names of your own.

    A mapping is used verbatim below its top level, so it must already be
    spelled the way OpenAPI spells it: ``operationId``, not ``operation_id``.
    Two consequences are worth knowing:

    - Typed objects always emit their defaults, so the typed form of an
      operation carries ``"deprecated": false`` where the mapping form
      carries nothing. The documents mean the same thing, but they are not
      byte-identical.
    - Specification extensions (``x-`` keys) are not supported at the top
      level of the path item, because a
      :class:`~dmr.openapi.objects.path_item.PathItem` has nowhere to keep
      them. They are rejected rather than dropped. Inside an operation they
      pass through untouched.

    Args:
        view_class: Any Django view class. It is not modified.
        openapi: Path item describing the view, either as
            :class:`~dmr.openapi.objects.path_item.PathItem`
            or as a plain mapping.
        components: Reusable components the path item references, either as
            :class:`~dmr.openapi.objects.components.Components`
            or as a plain mapping.

    Returns:
        A subclass of *view_class* that reports the given path item.

    Raises:
        TypeError: If a mapping contains a key that is not a path item field,
            or a component category that cannot be contributed.

    Warning:
        Adapting a view does **not** enrol it into the ``dmr`` request
        pipeline. No parsers, renderers, content negotiation, problem details,
        throttling, response validation or controller-level auth are applied
        to it, and its errors keep the shape Django gives them. The adapter
        adds visibility in the specification and nothing else.

    .. versionadded:: 0.13.0

    """
    namespace: dict[str, Any] = {
        '__doc__': view_class.__doc__,
        '__module__': view_class.__module__,
        '__qualname__': view_class.__qualname__,
        '_openapi': (
            openapi
            if isinstance(openapi, PathItem)
            else _build_path_item(openapi)
        ),
        '_openapi_components': _adapt_components(components),
    }
    return cast(
        'type[_ViewT]',
        type(view_class.__name__, (_AdaptedView, view_class), namespace),
    )


def _build_path_item(raw: RawPathItem) -> PathItem:
    field_names = {field.name for field in dataclasses.fields(PathItem)}
    fields: dict[str, Any] = {}

    for key, field_value in raw.items():
        name = 'ref' if key == _REF_KEY else key
        if name not in field_names:
            raise TypeError(
                f'{key!r} is not a supported OpenAPI path item field, '
                f'expected one of {sorted(field_names)}. '
                'Specification extensions are not supported here',
            )
        fields[name] = field_value

    return PathItem(**fields)


def _adapt_components(
    components: 'Components | RawComponents | None',
) -> Components | None:
    if components is None:
        return None
    if isinstance(components, Components):
        return _check_components(components)
    return _build_components(components)


def _build_components(raw: RawComponents) -> Components:
    fields: dict[str, Any] = {}

    for key, category in raw.items():
        name = _COMPONENT_FIELDS.get(key)
        if name is None:
            _reject_category(key)
        fields[name] = dict(category)

    return Components(**fields)


def _check_components(components: Components) -> Components:
    for field in dataclasses.fields(components):
        if (
            field.name not in ComponentRegistry.categories
            and getattr(components, field.name) is not None
        ):
            _reject_category(normalize_key(field.name))

    return components


def _reject_category(key: str) -> NoReturn:
    raise TypeError(
        f'{key!r} is not a component category an adapted view can '
        f'contribute, expected one of {sorted(_COMPONENT_FIELDS)}',
    )
