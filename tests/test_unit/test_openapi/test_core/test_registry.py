import pytest

from django_modern_rest.openapi.core.registry import OperationIdRegistry


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
