import pytest

from dmr.openapi.core.registry import (
    OperationIdRegistry,
    SchemaRegistry,
)
from dmr.openapi.objects.schema import Schema


class _TestClass:
    field: int


class _OtherTestClass:
    field: int


@pytest.fixture
def operation_id_registry() -> OperationIdRegistry:
    """Create ``OperationIdRegistry`` instance for testing."""
    return OperationIdRegistry()


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    """Create ``SchemaRegistry`` instance for testing."""
    return SchemaRegistry()


def test_multiple_unique_operation_ids(
    operation_id_registry: OperationIdRegistry,
) -> None:
    """Test that registering multiple unique operation IDs succeeds."""
    operation_ids = frozenset(
        ('getUsers', 'createUser', 'updateUser', 'deleteUser'),
    )

    for operation_id in operation_ids:
        operation_id_registry.register(operation_id)

    assert len(operation_id_registry._operation_ids) == len(operation_ids)
    assert operation_id_registry._operation_ids == operation_ids


def test_duplicate_operation_id_raises_error(
    operation_id_registry: OperationIdRegistry,
) -> None:
    """Test that registering a duplicate operation IDs raises ``ValueError``."""
    operation_id = 'getUsers'
    operation_id_registry.register(operation_id)

    with pytest.raises(
        ValueError,
        match=("Operation ID 'getUsers' is already registered"),
    ):
        operation_id_registry.register(operation_id)


def test_schema_register_returns_refs(schema_registry: SchemaRegistry) -> None:
    """Ensure registry correctly store class and return ``Reference``."""
    reference = schema_registry.register(
        _TestClass,
        _TestClass.__name__,
        Schema(),
    )

    assert len(schema_registry.schemas) == 1
    assert len(schema_registry._type_map) == 1
    assert reference.ref == f'#/components/schemas/{_TestClass.__name__}'


def test_schema_register_existing_type(schema_registry: SchemaRegistry) -> None:
    """Ensure registering an existing type returns the existing reference."""
    schema_registry.register(_TestClass, _TestClass.__name__, Schema())
    reference = schema_registry.register(
        _TestClass,
        _TestClass.__name__,
        Schema(),
    )

    assert reference.ref == f'#/components/schemas/{_TestClass.__name__}'
    assert len(schema_registry.schemas) == 1


def test_schema_register_name_collision(
    schema_registry: SchemaRegistry,
) -> None:
    """Ensure name collision is handled by appending a counter."""
    schema_registry.register(_TestClass, _TestClass.__name__, Schema())
    reference = schema_registry.register(
        _OtherTestClass,
        _TestClass.__name__,
        Schema(),
    )

    assert reference.ref == f'#/components/schemas/{_TestClass.__name__}1'
    assert len(schema_registry.schemas) == 2
    assert _TestClass.__name__ in schema_registry.schemas
