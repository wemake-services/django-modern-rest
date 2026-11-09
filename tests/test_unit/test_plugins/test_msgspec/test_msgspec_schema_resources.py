"""Msgspec resource-local definitions regression tests for issue #1707."""

from http import HTTPStatus
from typing import Annotated, Any

import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from dmr import Body, Controller
from dmr.openapi import build_schema
from dmr.openapi.mappers.schema_resources import SchemaResourceWarning
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.plugins.msgspec.schema import MsgspecSchemaGenerator
from dmr.routing import Router, path
from dmr.test import DMRRequestFactory


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
