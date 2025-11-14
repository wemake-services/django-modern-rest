from typing import Final

import pytest

from django_modern_rest.openapi.core.registry import SchemaRegistry
from django_modern_rest.openapi.objects import OpenAPIType, Reference, Schema

_SCHEMA_NAME: Final = 'TestSchema'


@pytest.fixture
def registry() -> SchemaRegistry:
    """Create test schema registry."""
    return SchemaRegistry()


def test_registry_contains(registry: SchemaRegistry) -> None:
    """Ensure __contains__ method works correctly."""
    assert _SCHEMA_NAME not in registry

    schema = Schema(type=OpenAPIType.STRING)
    registry.register(_SCHEMA_NAME, schema)
    assert _SCHEMA_NAME in registry


def test_registry_register_idempotency(registry: SchemaRegistry) -> None:
    """Ensure register does not overwrite existing schemas."""
    schema1 = Schema(type=OpenAPIType.STRING, min_length=1)
    registry.register(_SCHEMA_NAME, schema1)

    schema2 = Schema(type=OpenAPIType.INTEGER)
    registry.register(_SCHEMA_NAME, schema2)

    assert registry.all()[_SCHEMA_NAME] == schema1
    assert registry.all()[_SCHEMA_NAME] != schema2


def test_registry_reference_skip(registry: SchemaRegistry) -> None:
    """Ensure registry skip `Reference` objects."""
    registry.register(_SCHEMA_NAME, Reference(ref='test'))

    assert _SCHEMA_NAME not in registry
