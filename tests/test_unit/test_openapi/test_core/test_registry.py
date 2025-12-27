from typing import Final

import pytest

from django_modern_rest.openapi.core.registry import (
    OperationIdRegistry,
    SchemaRegistry,
)
from django_modern_rest.openapi.objects import OpenAPIType, Reference, Schema

_SCHEMA_NAME: Final = 'TestSchema'


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    """Create test schema registry."""
    return SchemaRegistry()


@pytest.fixture
def operation_registry() -> OperationIdRegistry:
    """Create OperationIdRegistry instance for testing."""
    return OperationIdRegistry()


def test_registry_contains(schema_registry: SchemaRegistry) -> None:
    """Ensure __contains__ method works correctly."""
    assert _SCHEMA_NAME not in schema_registry

    schema = Schema(type=OpenAPIType.STRING)
    schema_registry.register(_SCHEMA_NAME, schema)
    assert _SCHEMA_NAME in schema_registry


def test_registry_register_idempotency(schema_registry: SchemaRegistry) -> None:
    """Ensure register does not overwrite existing schemas."""
    schema1 = Schema(type=OpenAPIType.STRING, min_length=1)
    schema_registry.register(_SCHEMA_NAME, schema1)

    schema2 = Schema(type=OpenAPIType.INTEGER)
    schema_registry.register(_SCHEMA_NAME, schema2)

    assert schema_registry.all()[_SCHEMA_NAME] == schema1
    assert schema_registry.all()[_SCHEMA_NAME] != schema2


def test_registry_reference_skip(schema_registry: SchemaRegistry) -> None:
    """Ensure registry skip `Reference` objects."""
    schema_registry.register(_SCHEMA_NAME, Reference(ref='test'))

    assert _SCHEMA_NAME not in schema_registry


def test_multiple_unique_operation_ids(
    operation_registry: OperationIdRegistry,
) -> None:
    """Test that registering multiple unique operation IDs succeeds."""
    operation_ids = frozenset(
        ('getUsers', 'createUser', 'updateUser', 'deleteUser'),
    )

    for operation_id in operation_ids:
        operation_registry.register(operation_id)

    assert len(operation_registry._operation_ids) == len(operation_ids)
    assert operation_registry._operation_ids == operation_ids


def test_duplicate_operation_id_raises_error(
    operation_registry: OperationIdRegistry,
) -> None:
    """Test that registering a duplicate operation ID raises ValueError."""
    operation_id = 'getUsers'
    operation_registry.register(operation_id)

    with pytest.raises(
        ValueError,
        match=("Operation ID 'getUsers' is already registered"),
    ):
        operation_registry.register(operation_id)
