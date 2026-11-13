"""Resolve identified JSON Schema resources into document-local references."""

import dataclasses
import warnings
from collections.abc import Iterator
from typing import Any, TypeAlias
from urllib.parse import quote, unquote, urldefrag, urljoin

from dmr.openapi.mappers.schema_normalization import DumpedSchema, dump_field
from dmr.openapi.objects.schema import Schema

_Path: TypeAlias = tuple[str, ...]
_AnchorKey: TypeAlias = tuple[str, str]

_SCHEMA_MAPS = frozenset((
    'properties',
    'pattern_properties',
    'defs',
    'dependent_schemas',
))
_SCHEMA_LISTS = frozenset(('all_of', 'any_of', 'one_of', 'prefix_items'))
_SCHEMA_VALUES = frozenset((
    'items',
    'additional_properties',
    'contains',
    'property_names',
    'schema_not',
    'schema_if',
    'schema_then',
    'schema_else',
    'unevaluated_items',
    'unevaluated_properties',
    'content_schema',
))
_SCHEMA_KEYWORDS = _SCHEMA_MAPS | _SCHEMA_LISTS | _SCHEMA_VALUES


class SchemaResourceWarning(UserWarning):
    """A resource identifier was replaced with document-local references."""


@dataclasses.dataclass(slots=True)
class _Index:
    """Resource scopes collected from every schema node in the document."""

    resources: dict[str, _Path]
    scopes: dict[_Path, str]
    anchors: dict[_AnchorKey, _Path]
    roots: set[_Path]


def bundle_schema_resources(
    document: DumpedSchema,
    original: Any,
) -> None:
    """
    Rewrite identified resources into document-local references.

    JSON Schema ``$id`` establishes a resource scope that OpenAPI validators
    do not follow, so ``#/$defs/...`` refs of a resource would otherwise be
    resolved against the OpenAPI document root and report a broken pointer.
    Definitions stay at their physical location: hoisting them would collide
    when two resources define the same name.

    Only real schema nodes are rewritten, values inside ``default``,
    ``example``, ``examples``, ``const``, ``enum``, and ``x-*`` are data.
    Resource identity is removed only after all references are rewritten,
    and nothing is cached when a reference cannot be resolved.

    .. versionadded:: 0.17.0
    """
    locations = dict(_schema_locations(original))
    index = _index(locations, document)
    if not index.resources:
        return
    _apply(document, locations, _replacements(locations, index), index)


def _apply(
    document: DumpedSchema,
    locations: dict[_Path, Schema],
    replacements: list[tuple[_Path, str]],
    index: _Index,
) -> None:
    warnings.warn(
        'JSON Schema $id resources were bundled into document-local '
        'references and their identifiers were removed.',
        SchemaResourceWarning,
        stacklevel=2,
    )
    for path, rewritten in replacements:
        _at(document, path)['$ref'] = rewritten
    for path, schema in locations.items():
        if schema.resource_id is not None:
            _at(document, path).pop('$id')
        if schema.anchor is not None and index.scopes[path] in index.resources:
            _at(document, path).pop('$anchor')


def _index(locations: dict[_Path, Schema], document: DumpedSchema) -> _Index:
    base = document.get('$self') or ''
    index = _Index({}, {}, {}, set())
    for path, schema in locations.items():
        scope = _with_resource(index, path, schema, document, base)
        index.scopes[path] = scope
        _with_anchor(index, path, schema, scope)
    return index


def _with_resource(
    index: _Index,
    path: _Path,
    schema: Schema,
    document: DumpedSchema,
    base: str,
) -> str:
    scope = _scope_of(path, index.scopes, base)
    if schema.resource_id is None:
        return scope
    resolved = urljoin(scope, schema.resource_id)
    if not resolved or urldefrag(resolved)[1]:
        raise ValueError(
            f'Invalid JSON Schema resource identifier: {resolved!r}',
        )
    resolved = urldefrag(resolved)[0]
    index.roots.add(path)
    previous = index.resources.setdefault(resolved, path)
    if previous != path and _at(document, previous) != _at(document, path):
        raise ValueError(
            f'Conflicting JSON Schema resource identifier: {resolved!r}',
        )
    return resolved


def _with_anchor(
    index: _Index,
    path: _Path,
    schema: Schema,
    scope: str,
) -> None:
    if schema.anchor is None:
        return
    key = (scope, schema.anchor)
    canonical = _canonical_path(index, path, scope)
    previous = index.anchors.setdefault(key, canonical)
    if previous != canonical:
        raise ValueError(f'Conflicting JSON Schema anchor: {key!r}')


def _canonical_path(index: _Index, path: _Path, scope: str) -> _Path:
    for length in range(len(path), 0, -1):
        if path[:length] in index.roots:
            return (*index.resources[scope], *path[length:])
    return path


def _scope_of(path: _Path, scopes: dict[_Path, str], base: str) -> str:
    for length in range(len(path) - 1, -1, -1):
        scope = scopes.get(path[:length])
        if scope is not None:
            return scope
    return base


def _replacements(
    locations: dict[_Path, Schema],
    index: _Index,
) -> list[tuple[_Path, str]]:
    replacements: list[tuple[_Path, str]] = []
    for path, schema in locations.items():
        scope = index.scopes[path]
        _forbid_dynamic(scope, schema, index)
        if schema.ref is not None:
            replacements.append((
                path,
                _rewrite(schema.ref, scope, index, locations),
            ))
    return replacements


def _forbid_dynamic(scope: str, schema: Schema, index: _Index) -> None:
    if schema.dynamic_ref is None and schema.dynamic_anchor is None:
        return
    target = urldefrag(_resolve_uri(scope, schema.dynamic_ref or ''))[0]
    if scope in index.resources or target in index.resources:
        raise ValueError(
            'Dynamic references in identified schema resources '
            'are not supported',
        )


def _rewrite(
    reference: str,
    scope: str,
    index: _Index,
    locations: dict[_Path, Schema],
) -> str:
    # Serializer-generated component refs always point at the document.
    if reference.startswith('#/components/schemas/'):
        return reference
    uri, fragment = urldefrag(_resolve_uri(scope, reference))
    resource = index.resources.get(uri)
    if resource is None:
        return _external_reference(reference, scope, index)
    target = _target(resource, uri, unquote(fragment), index.anchors)
    if target not in locations and not _boolean_target(target, locations):
        raise ValueError(
            f'JSON Schema reference does not identify a schema: {reference!r}',
        )
    return ''.join((
        '#/',
        '/'.join(_escape(token) for token in target),
    ))


def _boolean_target(target: _Path, locations: dict[_Path, Schema]) -> bool:
    parent = locations.get(target[:-1])
    if parent is None:
        return False
    for name in _SCHEMA_VALUES:
        field = next(
            field for field in dataclasses.fields(parent) if field.name == name
        )
        if dump_field(name, field.type) == target[-1]:
            return isinstance(getattr(parent, name), bool)
    return False


def _resolve_uri(scope: str, reference: str) -> str:
    # Opaque identifiers, like `urn:example:thing`, cannot be joined.
    if not reference or reference.startswith('#'):
        return scope + reference
    return urljoin(scope, reference)


def _external_reference(reference: str, scope: str, index: _Index) -> str:
    # Keep external references absolute once their base is being removed.
    if scope in index.resources:
        return _resolve_uri(scope, reference)
    return reference


def _target(
    resource: _Path,
    uri: str,
    fragment: str,
    anchors: dict[_AnchorKey, _Path],
) -> _Path:
    if not fragment:
        return resource
    if fragment.startswith('/'):
        return (*resource, *_tokens(fragment))
    anchor = anchors.get((uri, fragment))
    if anchor is None:
        raise ValueError(f'Unknown JSON Schema anchor: {fragment!r}')
    return anchor


def _tokens(fragment: str) -> tuple[str, ...]:
    return tuple(
        token.replace('~1', '/').replace('~0', '~')
        for token in fragment[1:].split('/')
    )


def _escape(token: str) -> str:
    return quote(token.replace('~', '~0').replace('/', '~1'), safe='~$')


def _step(node: Any, token: str) -> Any:
    mapping: Any = node
    if isinstance(node, list):
        return mapping[int(token)]
    return mapping[token]


def _at(document: Any, path: _Path) -> Any:
    node: Any = document
    for token in path:
        node = _step(node, token)
    return node


def _schema_locations(
    node: Any,
    path: _Path = (),
) -> Iterator[tuple[_Path, Schema]]:
    if isinstance(node, Schema):
        return _schema_children(node, path)
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        return _dataclass_children(node, path)
    return _container_children(node, path)


def _schema_children(
    schema: Schema,
    path: _Path,
) -> Iterator[tuple[_Path, Schema]]:
    yield path, schema
    for field in dataclasses.fields(schema):
        if field.name not in _SCHEMA_KEYWORDS:
            continue
        yield from _keyword_children(
            field.name,
            dump_field(field.name, field.type),
            getattr(schema, field.name),
            path,
        )


def _keyword_children(
    name: str,
    keyword: str,
    raw_value: Any,
    path: _Path,
) -> Iterator[tuple[_Path, Schema]]:
    keyword_path = (*path, keyword)
    if raw_value is None:
        return
    if name in _SCHEMA_MAPS:
        yield from _mapping_locations(raw_value, keyword_path)
        return
    if name in _SCHEMA_LISTS:
        yield from _sequence_locations(raw_value, keyword_path)
        return
    yield from _schema_locations(raw_value, keyword_path)


def _mapping_locations(
    raw_value: Any,
    path: _Path,
) -> Iterator[tuple[_Path, Schema]]:
    for key, child in raw_value.items():
        yield from _schema_locations(child, (*path, key))


def _sequence_locations(
    raw_value: Any,
    path: _Path,
) -> Iterator[tuple[_Path, Schema]]:
    for position, child in enumerate(raw_value):
        yield from _schema_locations(child, (*path, str(position)))


def _dataclass_children(
    node: Any,
    path: _Path,
) -> Iterator[tuple[_Path, Schema]]:
    for field in dataclasses.fields(node):
        if field.name.startswith('_') or field.name == 'x_extensions':
            continue
        yield from _schema_locations(
            getattr(node, field.name),
            (*path, dump_field(field.name, field.type)),
        )


def _container_children(
    node: Any,
    path: _Path,
) -> Iterator[tuple[_Path, Schema]]:
    if isinstance(node, dict):
        yield from _mapping_locations(node, path)
    elif isinstance(node, list):
        yield from _sequence_locations(node, path)
