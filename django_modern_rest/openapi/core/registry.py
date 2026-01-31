from typing import Any

from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.schema import Schema


class OperationIdRegistry:
    """Registry for OpenAPI operation IDs."""

    def __init__(self) -> None:
        """Initialize an empty operation ids registry."""
        self._operation_ids: set[str] = set()

    def register(self, operation_id: str) -> None:
        """Register a operation ID in the registry."""
        if operation_id in self._operation_ids:
            raise ValueError(
                f'Operation ID {operation_id!r} is already registered in the '
                'OpenAPI specification. Operation IDs must be unique across '
                'all endpoints to ensure proper API documentation. '
                'Please use a different operation ID for this endpoint.',
            )

        self._operation_ids.add(operation_id)


class SchemaRegistry:
    """Registry for Schemas."""

    def __init__(self) -> None:
        """Initialize empty schema and type registers."""
        self._schemas: dict[str, Schema] = {}
        self._type_map: dict[Any, str] = {}

    def register(
        self,
        source_type: Any,
        name: str,
        schema: Schema,
    ) -> Reference:
        """Register Schema in registry."""
        registered_name = self._type_map.get(source_type)
        if registered_name is not None:
            raise ValueError(
                f'Type {source_type!r} is already registered.',
            )

        if name in self._schemas:
            raise ValueError(
                f'Schema name {name!r} is already used by another type.',
            )

        self._schemas[name] = schema
        self._type_map[source_type] = name
        return self._make_reference(name)

    def _make_reference(self, name: str) -> Reference:
        return Reference(ref=f'#/components/schemas/{name}')
