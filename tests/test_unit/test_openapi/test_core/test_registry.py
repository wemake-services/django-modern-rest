import pytest

from django_modern_rest.openapi.core.registry import (
    OperationIdRegistry,
    SchemaRegistry,
)
from django_modern_rest.openapi.objects.schema import Schema


class _TestClass:
    field: int


class _OtherTestClass:
    field: int


@pytest.fixture
def registry() -> OperationIdRegistry:
    """Create OperationIdRegistry instance for testing."""
    return OperationIdRegistry()


def test_multiple_unique_operation_ids(registry: OperationIdRegistry) -> None:
    """Test that registering multiple unique operation IDs succeeds."""
    operation_ids = frozenset(
        ('getUsers', 'createUser', 'updateUser', 'deleteUser'),
    )

    for operation_id in operation_ids:
        registry.register(operation_id)

    assert len(registry._operation_ids) == len(operation_ids)
    assert registry._operation_ids == operation_ids


def test_duplicate_operation_id_raises_error(
    registry: OperationIdRegistry,
) -> None:
    """Test that registering a duplicate operation ID raises ValueError."""
    operation_id = 'getUsers'
    registry.register(operation_id)

    with pytest.raises(
        ValueError,
        match=("Operation ID 'getUsers' is already registered"),
    ):
        registry.register(operation_id)


def test_schema_register_returns_refs() -> None:
    """Ensure SchemaRegistry correctly store class and return Reference."""
    registry = SchemaRegistry()
    reference = registry.register(_TestClass, _TestClass.__name__, Schema())

    assert len(registry._schemas) == 1
    assert len(registry._type_map) == 1
    assert reference.ref == f'#/components/schemas/{_TestClass.__name__}'


def test_schema_register_raise_errors() -> None:
    """Ensure SchemaRegistry raises errors."""
    registry = SchemaRegistry()
    registry.register(_TestClass, _TestClass.__name__, Schema())

    with pytest.raises(
        ValueError,
        match=('already registered'),
    ):
        registry.register(_TestClass, _TestClass.__name__, Schema())

    with pytest.raises(
        ValueError,
        match=('is already used'),
    ):
        registry.register(_OtherTestClass, _TestClass.__name__, Schema())
