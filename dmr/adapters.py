"""
Adapters that make plain Django views visible in the OpenAPI specification.

An adapted view is documented, not adopted: it keeps dispatching exactly
as it would under plain ``django.urls.path``. See :func:`adapt_django_view`.
"""

import dataclasses
import re
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
from dmr.openapi.objects import (
    Components,
    Discriminator,
    PathItem,
    Reference,
)
from dmr.openapi.objects.openapi import normalize_key

if TYPE_CHECKING:
    from _typeshed import DataclassInstance
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

#: Discriminator keys, the one place a reference has no ``$ref`` key.
_DISCRIMINATOR_KEY: Final = 'discriminator'
_MAPPING_KEY: Final = 'mapping'

#: Contributable component categories, keyed by their document spelling.
_COMPONENT_FIELDS: Final = MappingProxyType({
    normalize_key(category): category
    for category in ComponentRegistry.categories
})

#: Reference targets a prefix applies to, one per contributable category.
_REF_BASES: Final = tuple(
    f'#/components/{category}/' for category in _COMPONENT_FIELDS
)

#: The characters an OpenAPI component name is allowed to be spelled with.
_COMPONENT_NAME_PATTERN: Final = re.compile(r'[a-zA-Z0-9._-]*')


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
    component_prefix: str = '',
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
    generates from controllers, and names imported from a foreign description
    are rarely unique enough for that. Pass *component_prefix* to namespace
    the whole description — the component names and every reference to them,
    in the path item and nested inside other components alike:

    .. code:: python

        >>> LegacyExport = adapt_django_view(
        ...     LegacyExportView,
        ...     openapi={
        ...         'get': {
        ...             'responses': {
        ...                 '200': {'$ref': '#/components/responses/Csv'},
        ...             },
        ...         },
        ...     },
        ...     components={
        ...         'responses': {'Csv': {'description': 'CSV payload'}},
        ...     },
        ...     component_prefix='Legacy',
        ... )

    That view is documented under ``#/components/responses/LegacyCsv``,
    leaving a ``Csv`` of the project's own untouched. The prefix describes
    the view rather than its contribution, so a view that only references
    what another view under the same prefix contributes takes it too.

    Because the prefix is applied to every reference, a description that
    points at a component the framework generates should not carry one.

    Two definitions that end up under the same final name are reported as an
    error rather than silently merged, whether they come from two adapted
    views or from a view and the framework's own schemas.

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
        component_prefix: Namespace for the component names of this view and
            for every reference to them. Empty by default, which documents
            the view under the names it was given.

    Returns:
        A subclass of *view_class* that reports the given path item.

    Raises:
        TypeError: If a mapping contains a key that is not a path item field,
            or a component category that cannot be contributed.
        ValueError: If *component_prefix* cannot spell a component name.

    Warning:
        Adapting a view does **not** enrol it into the ``dmr`` request
        pipeline. No parsers, renderers, content negotiation, problem details,
        throttling, response validation or controller-level auth are applied
        to it, and its errors keep the shape Django gives them. The adapter
        adds visibility in the specification and nothing else.

    .. versionadded:: 0.13.0

    """
    _check_prefix(component_prefix)
    path_item = (
        openapi if isinstance(openapi, PathItem) else _build_path_item(openapi)
    )
    adapted_components = _adapt_components(components)
    if component_prefix:
        path_item = cast(
            'PathItem',
            _prefix_refs(path_item, component_prefix),
        )
        adapted_components = _prefix_components(
            adapted_components,
            component_prefix,
        )

    namespace: dict[str, Any] = {
        '__doc__': view_class.__doc__,
        '__module__': view_class.__module__,
        '__qualname__': view_class.__qualname__,
        '_openapi': path_item,
        '_openapi_components': adapted_components,
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


def _check_prefix(prefix: str) -> None:
    if _COMPONENT_NAME_PATTERN.fullmatch(prefix) is None:
        raise ValueError(
            f'{prefix!r} cannot prefix an OpenAPI component name, which is '
            'spelled with letters, digits, dots, dashes and underscores only',
        )


def _prefix_components(
    components: Components | None,
    prefix: str,
) -> Components | None:
    if components is None:
        return None

    namespaced: dict[str, Any] = {}
    for category in ComponentRegistry.categories:
        entries = getattr(components, category)
        if entries is not None:
            namespaced[category] = {
                f'{prefix}{name}': _prefix_refs(component, prefix)
                for name, component in entries.items()
            }

    return dataclasses.replace(components, **namespaced)


def _prefix_refs(node: Any, prefix: str) -> Any:
    if isinstance(node, Mapping):
        return _prefix_mapping_refs(node, prefix)  # pyright: ignore[reportUnknownArgumentType]
    if isinstance(node, list):
        return _prefix_list_refs(node, prefix)  # pyright: ignore[reportUnknownArgumentType]
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        return _prefix_object_refs(node, prefix)
    return node


def _prefix_mapping_refs(
    node: Mapping[str, Any],
    prefix: str,
) -> dict[str, Any]:
    return {
        key: _prefix_keyed_value(key, node_value, prefix)
        for key, node_value in node.items()
    }


def _prefix_keyed_value(key: str, node_value: Any, prefix: str) -> Any:
    if key == _REF_KEY and isinstance(node_value, str):
        return _prefix_ref(node_value, prefix)
    if key == _DISCRIMINATOR_KEY and isinstance(node_value, Mapping):
        return _prefix_raw_discriminator(node_value, prefix)  # pyright: ignore[reportUnknownArgumentType]
    return _prefix_refs(node_value, prefix)


def _prefix_raw_discriminator(
    node: Mapping[str, Any],
    prefix: str,
) -> dict[str, Any]:
    return {
        key: (
            _prefix_discriminator_targets(node_value, prefix)
            if key == _MAPPING_KEY
            else node_value
        )
        for key, node_value in node.items()
    }


def _prefix_discriminator_targets(
    mapping: Mapping[str, str] | None,
    prefix: str,
) -> dict[str, str] | None:
    if mapping is None:
        return None
    return {
        payload: _prefix_schema_target(target, prefix)
        for payload, target in mapping.items()
    }


def _prefix_schema_target(target: str, prefix: str) -> str:
    if '/' in target:
        return _prefix_ref(target, prefix)
    # A discriminator may also name a schema outright, which the
    # specification resolves against `#/components/schemas/` for us:
    return f'{prefix}{target}'


def _prefix_list_refs(node: list[Any], prefix: str) -> list[Any]:
    return [_prefix_refs(list_item, prefix) for list_item in node]


def _prefix_object_refs(node: 'DataclassInstance', prefix: str) -> Any:
    if isinstance(node, Reference):
        return dataclasses.replace(node, ref=_prefix_ref(node.ref, prefix))
    if isinstance(node, Discriminator):
        return dataclasses.replace(
            node,
            mapping=_prefix_discriminator_targets(node.mapping, prefix),
        )

    return dataclasses.replace(
        node,
        **{
            field.name: _prefix_refs(getattr(node, field.name), prefix)
            for field in dataclasses.fields(node)
            if field.init
        },
    )


def _prefix_ref(ref: str, prefix: str) -> str:
    for base in _REF_BASES:
        if ref.startswith(base):
            return f'{base}{prefix}{ref.removeprefix(base)}'
    return ref


def _reject_category(key: str) -> NoReturn:
    raise TypeError(
        f'{key!r} is not a component category an adapted view can '
        f'contribute, expected one of {sorted(_COMPONENT_FIELDS)}',
    )
