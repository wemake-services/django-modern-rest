import pytest

from dmr.openapi.core.registry import OperationIdRegistry


class _TestClass:
    field: int


class _OtherTestClass:
    field: int


def test_multiple_unique_operation_ids() -> None:
    """Test that registering multiple unique operation IDs succeeds."""
    operation_id_registry = OperationIdRegistry()
    operation_ids = frozenset(
        ('getUsers', 'createUser', 'updateUser', 'deleteUser'),
    )

    for operation_id in operation_ids:
        operation_id_registry.register(operation_id)

    assert len(operation_id_registry._operation_ids) == len(operation_ids)
    assert operation_id_registry._operation_ids == operation_ids


def test_duplicate_operation_id_raises_error() -> None:
    """Test that registering a duplicate operation IDs raises ``ValueError``."""
    operation_id_registry = OperationIdRegistry()
    operation_id = 'getUsers'
    operation_id_registry.register(operation_id)

    with pytest.raises(
        ValueError,
        match=("Operation ID 'getUsers' is already registered"),
    ):
        operation_id_registry.register(operation_id)
