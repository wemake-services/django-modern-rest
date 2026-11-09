"""Regression tests for identified JSON Schema resources (issue #1707)."""

from http import HTTPStatus
from typing import Annotated, Any, Final, cast

import msgspec
import pytest

from dmr import Body, Controller
from dmr.openapi import build_schema
from dmr.openapi.mappers.schema_loader import load_schema
from dmr.openapi.mappers.schema_normalization import dump_schema
from dmr.openapi.mappers.schema_resources import SchemaResourceWarning
from dmr.openapi.objects import Components, Info
from dmr.openapi.openapi import OpenAPI
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.plugins.msgspec.schema import MsgspecSchemaGenerator
from dmr.routing import Router, path
from dmr.test import DMRRequestFactory

_PREFIX: Final = '#/components/schemas/Model'
_POINT: Final = f'{_PREFIX}/$defs/Child/$defs/Point'
_CHILD: Final = f'{_PREFIX}/$defs/Child'


def _scoped_schema() -> dict[str, Any]:
    return {
        '$id': 'https://example.com/root.json',
        '$defs': {
            'Child': {
                '$id': 'child.json',
                '$anchor': 'child',
                'type': 'object',
                '$defs': {'Point': {'type': 'integer'}},
                'properties': {
                    'self': {'$ref': '#'},
                    'point': {'$ref': '#/$defs/Point'},
                    'parent': {'$ref': 'root.json'},
                    'external': {'$ref': 'external.json'},
                },
            },
        },
        'properties': {
            'forward': {'$ref': 'child.json#child'},
            'crossing': {'$ref': '#/$defs/Child/$defs/Point'},
            'inherited': {
                '$defs': {'Point': {'type': 'string'}},
                'properties': {'point': {'$ref': '#/$defs/Child/$defs/Point'}},
            },
        },
    }


def _document(raw: dict[str, Any]) -> OpenAPI:
    return OpenAPI(
        info=Info(title='Resources', version='1'),
        openapi='3.1.0',
        components=Components(schemas={'Model': load_schema(raw)}),
    )


def _converted(document: OpenAPI) -> dict[str, Any]:
    with pytest.warns(SchemaResourceWarning):
        converted = document.convert(skip_validation=True)
    schemas = converted['components']['schemas']
    return cast('dict[str, Any]', schemas['Model'])


def _round_trip(document: OpenAPI) -> dict[str, Any]:
    components = document.components
    assert components is not None
    schemas = components.schemas
    assert schemas is not None
    return dump_schema(schemas['Model'])


@pytest.mark.parametrize(
    'identifier',
    [
        'https://example.com/polygon.json',
        'urn:example:polygon',
        'https://example.com/polygon.json#',
    ],
)
def test_resource_local_reference(identifier: str) -> None:
    """Resolve local definitions independently of the document root."""
    raw = {
        '$id': identifier,
        'type': 'object',
        '$defs': {'Point': {'type': 'integer'}},
        'properties': {'point': {'$ref': '#/$defs/Point'}},
    }
    document = _document(raw)
    assert _round_trip(document) == raw
    with pytest.warns(SchemaResourceWarning):
        converted = document.convert()
    model = converted['components']['schemas']['Model']
    assert '$id' not in model
    assert model['properties']['point']['$ref'] == f'{_PREFIX}/$defs/Point'
    assert document.convert() is converted
    document.cache_clear()
    with pytest.warns(SchemaResourceWarning):
        assert document.convert(skip_validation=True) == converted
    assert document.convert() == converted


def test_document_without_resources_is_unchanged() -> None:
    """Ordinary schemas keep their existing serialization behaviour."""
    document = _document({'type': 'string'})
    assert document.convert(skip_validation=True) == dump_schema(document)


def test_resource_in_schema_sequence() -> None:
    """Rewrite a resource within an array and preserve unscoped references."""
    document = _document({
        'allOf': [
            {
                '$id': 'https://example.com/item',
                '$ref': '#',
            },
            {'$ref': 'external.json'},
        ],
    })
    model = _converted(document)
    assert model['allOf'] == [
        {'$ref': f'{_PREFIX}/allOf/0'},
        {'$ref': 'external.json'},
    ]


def test_resource_identifiers_are_rewritten() -> None:
    """Resolve anchor, sibling and external references after bundling."""
    model = _converted(_document(_scoped_schema()))
    child = model['$defs']['Child']
    assert '$id' not in child
    assert child['properties'] == {
        'self': {'$ref': _CHILD},
        'point': {'$ref': _POINT},
        'parent': {'$ref': _PREFIX},
        'external': {'$ref': 'https://example.com/external.json'},
    }
    assert model['properties']['forward']['$ref'] == _CHILD
    assert model['properties']['crossing']['$ref'] == _POINT


@pytest.mark.parametrize('keyword', ['items', 'additionalProperties'])
@pytest.mark.parametrize('allowed', [True, False])
def test_boolean_reference_target(keyword: str, *, allowed: bool) -> None:
    """Boolean schemas remain valid reference targets."""
    model = _converted(
        _document({
            '$id': 'https://example.com/boolean',
            keyword: allowed,
            '$ref': f'#/{keyword}',
        }),
    )
    assert model[keyword] is allowed
    assert model['$ref'] == f'{_PREFIX}/{keyword}'


def test_identical_resource_anchor_copies() -> None:
    """Repeated identical resource schemas share their canonical anchor."""
    resource = {
        '$id': 'https://example.com/copied',
        '$anchor': 'node',
        'properties': {'self': {'$ref': '#node'}},
    }
    model = _converted(_document({'allOf': [resource, resource]}))
    assert model['allOf'] == [
        {'properties': {'self': {'$ref': f'{_PREFIX}/allOf/0'}}},
        {'properties': {'self': {'$ref': f'{_PREFIX}/allOf/0'}}},
    ]


def test_bundled_anchor_does_not_leak() -> None:
    """Flattened resource anchors do not shadow an enclosing anchor."""
    model = _converted(
        _document({
            '$defs': {
                'Resource': {
                    '$id': 'https://example.com/anchored',
                    '$anchor': 'node',
                    'type': 'integer',
                },
                'Local': {'$anchor': 'node', 'type': 'string'},
            },
            '$ref': '#node',
        }),
    )
    assert '$anchor' not in model['$defs']['Resource']
    assert model['$defs']['Local']['$anchor'] == 'node'
    assert model['$ref'] == '#node'


@pytest.mark.parametrize('bundled', [True, False])
def test_dynamic_reference_to_resource(*, bundled: bool) -> None:
    """Fail before stripping an ID used by an incoming dynamic reference."""
    document = _document({
        '$defs': {'Resource': {'$id': 'https://example.com/dynamic'}},
        '$dynamicRef': (
            'https://example.com/dynamic' if bundled else 'external.json'
        ),
    })
    if bundled:
        with pytest.raises(ValueError, match='Dynamic references'):
            document.convert(skip_validation=True)
    else:
        assert _converted(document)['$dynamicRef'] == 'external.json'


def test_nested_definitions_keep_their_scope() -> None:
    """Do not resolve a nested reference against the nearest `$defs`."""
    model = _converted(_document(_scoped_schema()))
    inherited = model['properties']['inherited']['properties']['point']
    assert inherited['$ref'] == _POINT


def test_instance_data_and_pointer_escaping() -> None:
    """Never interpret literal schema-looking instance values as schemas."""
    literal = {'$id': 'do-not-touch', '$ref': '#', '$defs': {'X': {}}}
    document = _document({
        '$id': 'https://example.com/model',
        '$defs': {'a/b~ 空#%': {'type': 'string'}},
        'properties': {'value': {'$ref': '#/$defs/a~1b~0%20%E7%A9%BA%23%25'}},
        'default': literal,
        'example': literal,
        'examples': [literal],
        'const': literal,
        'enum': [literal],
        'x-payload': literal,
    })
    model = _converted(document)
    escaped = model['properties']['value']
    assert escaped['$ref'] == f'{_PREFIX}/$defs/a~1b~0%20%E7%A9%BA%23%25'
    for keyword in ('default', 'example', 'const', 'x-payload'):
        assert model[keyword] == literal
    assert model['examples'] == [literal]
    assert model['enum'] == [literal]


@pytest.mark.parametrize(
    ('raw', 'message'),
    [
        (
            {'$id': 'https://example.com/root#bad'},
            'Invalid JSON Schema resource',
        ),
        (
            {'$id': 'https://example.com/root', '$ref': '#/missing'},
            'does not identify a schema',
        ),
        (
            {'$id': 'https://example.com/root', '$ref': '#/absent/child'},
            'does not identify a schema',
        ),
        (
            {'$id': 'https://example.com/root', '$ref': '#missing'},
            'Unknown JSON Schema anchor',
        ),
        (
            {'$id': 'https://example.com/root', '$dynamicRef': '#node'},
            'Dynamic references',
        ),
        (
            {'$id': 'https://example.com/root', '$dynamicAnchor': 'node'},
            'Dynamic references',
        ),
        (
            {
                '$id': 'https://example.com/root',
                '$defs': {
                    'A': {'$id': 'duplicate', 'type': 'integer'},
                    'B': {'$id': 'duplicate', 'type': 'string'},
                },
            },
            'Conflicting JSON Schema resource',
        ),
        (
            {
                '$id': 'https://example.com/root',
                '$defs': {
                    'A': {'$anchor': 'duplicate'},
                    'B': {'$anchor': 'duplicate'},
                },
            },
            'Conflicting JSON Schema anchor',
        ),
    ],
)
def test_invalid_resource_is_not_cached(
    raw: dict[str, Any],
    message: str,
) -> None:
    """Fail explicitly instead of caching a partially normalized document."""
    document = _document(raw)
    for _ in range(2):
        with pytest.raises(ValueError, match=message):
            document.convert(skip_validation=True)


def test_msgspec_resource_integration(dmr_rf: DMRRequestFactory) -> None:
    """The issue's nested resource validates and does not collide with Point."""

    class Point(msgspec.Struct):
        label: str

    class Shape(msgspec.Struct):
        point: Point
        polygon: Annotated[
            dict[str, Any],
            msgspec.Meta(
                extra_json_schema={
                    '$id': 'https://example.com/polygon',
                    '$defs': {'Point': {'type': 'integer'}},
                    'properties': {'point': {'$ref': '#/$defs/Point'}},
                },
            ),
        ]
        other: Annotated[
            dict[str, Any],
            msgspec.Meta(
                extra_json_schema={
                    '$id': 'https://example.com/other',
                    '$defs': {'Point': {'type': 'string'}},
                    'properties': {'point': {'$ref': '#/$defs/Point'}},
                },
            ),
        ]

    class ShapeController(Controller[MsgspecSerializer]):
        def post(self, parsed_body: Body[Shape]) -> str:
            return 'ok'

    assert (
        ShapeController.as_view()(
            dmr_rf.post(
                '/shape/',
                data={
                    'point': {'label': 'test'},
                    'polygon': {'point': 1},
                    'other': {'point': 'test'},
                },
            ),
        ).status_code
        == HTTPStatus.CREATED
    )
    document = build_schema(
        Router('api/', [path('shape/', ShapeController.as_view())]),
    )
    with pytest.warns(SchemaResourceWarning):
        schemas = document.convert()['components']['schemas']
    assert schemas['Point']['properties']['label']['type'] == 'string'
    for field, expected_type in (('polygon', 'integer'), ('other', 'string')):
        schema = schemas['Shape']['properties'][field]
        assert schema['$defs']['Point']['type'] == expected_type
        assert schema['properties']['point']['$ref'] == (
            f'#/components/schemas/Shape/properties/{field}/$defs/Point'
        )


def test_msgspec_root_resource_keeps_definitions() -> None:
    """Do not hoist an identified resource's own definitions as components."""
    resource = Annotated[
        dict[str, Any],
        msgspec.Meta(
            extra_json_schema={
                '$id': 'https://example.com/root',
                '$defs': {'Point': {'type': 'integer'}},
                'properties': {'point': {'$ref': '#/$defs/Point'}},
            },
        ),
    ]

    root, components = MsgspecSchemaGenerator.get_schema(
        resource,
        '#/components/schemas/',
    )

    assert root['$id'] == 'https://example.com/root'
    assert root['$defs'] == {'Point': {'type': 'integer'}}
    assert components == {}


def test_unidentified_root_definitions_hoist() -> None:
    """Keep the historical extraction for unidentified root definitions."""
    custom = Annotated[
        dict[str, Any],
        msgspec.Meta(
            extra_json_schema={
                '$ref': '#/components/schemas/_Placeholder',
                '$defs': {'_Placeholder': {'type': 'object'}},
            },
        ),
    ]

    root, components = MsgspecSchemaGenerator.get_schema(
        custom,
        '#/components/schemas/',
    )

    assert '$defs' not in root
    assert components == {'_Placeholder': {'type': 'object'}}
