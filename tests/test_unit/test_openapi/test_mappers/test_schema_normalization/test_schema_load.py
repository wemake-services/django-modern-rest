import dataclasses
import json
from collections.abc import Callable
from typing import Any

import pytest
import yaml
from syrupy.assertion import SnapshotAssertion

from dmr.openapi import load_schema
from dmr.openapi.mappers.schema_normalization import dump_schema
from dmr.openapi.objects import (
    Components,
    Example,
    Link,
    PathItem,
    Schema,
)
from dmr.openapi.openapi import OpenAPI


def test_load_schema(
    snapshot: SnapshotAssertion,
    named_text_fixture: Callable[[str], str],
) -> None:
    """Ensure that ``dump_field`` converts field names to OpenAPI keys."""
    schema = yaml.safe_load(named_text_fixture('django-allauth.yml'))

    loaded = load_schema(schema, OpenAPI)
    assert isinstance(loaded, OpenAPI)

    dumped = dump_schema(loaded)
    assert json.dumps(dumped, indent=2) == snapshot
    assert dumped['components'].keys() == schema['components'].keys()
    assert isinstance(dumped['x-tagGroups'], list)
    for field in dataclasses.fields(Components):
        if field.name not in schema['components']:
            continue

        assert (
            dumped['components'][field.name].keys()
            == schema['components'][field.name].keys()
        )


@pytest.mark.parametrize(
    ('model', 'unstructured'),
    [
        (Schema, {'type': 'string', 'default': None}),
        (Schema, {'const': None, 'example': None}),
        (Example, {'value': None, 'dataValue': None}),
        (Link, {'requestBody': None}),
    ],
)
def test_load_schema_none_values(
    *,
    model: type[Any],
    unstructured: dict[str, Any],
) -> None:
    """Ensure that ``None`` values survive the load and dump round trip."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1619
    loaded = load_schema(unstructured, model)

    assert isinstance(loaded, model)
    assert dump_schema(loaded) == unstructured


def test_load_schema_x_extensions() -> None:
    """Extensions are loaded into ``x_extensions`` of the matching objects."""
    unstructured = {
        'summary': 'Users',
        'get': {
            'parameters': [
                {'name': 'search', 'in': 'query', 'x-searchable': True},
                {'$ref': '#/components/parameters/Page'},
            ],
            'responses': {'200': {'description': 'OK', 'x-cacheable': True}},
            'x-audience': 'public',
        },
        'x-owner': 'team-users',
    }

    loaded = load_schema(unstructured, PathItem)

    assert dump_schema(loaded) == unstructured


def test_load_schema_x_extensions_map_keys() -> None:
    """Map keys that start with ``x-`` are not extensions."""
    unstructured = {
        'type': 'object',
        'properties': {'x-key': {'type': 'string', 'x-range': {'min': 0}}},
        'x-top': True,
    }

    loaded = load_schema(unstructured, Schema)
    assert dump_schema(loaded) == unstructured
