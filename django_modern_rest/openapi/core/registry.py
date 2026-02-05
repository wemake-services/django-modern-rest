from typing import Any, ClassVar

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

    schema_prefix: ClassVar[str] = '#/components/schemas/'

    def __init__(self) -> None:
        """Initialize empty schema and type registers."""
        self.schemas: dict[str, Schema] = {}
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
            return self._make_reference(registered_name)

        name = self._get_unique_name(name)
        self.schemas[name] = schema
        self._type_map[source_type] = name
        return self._make_reference(name)

    def get_reference(self, source_type: Any) -> Reference | None:
        """Get registered reference."""
        name = self._type_map.get(source_type)
        if name:
            return self._make_reference(name)
        return None

    def _make_reference(self, name: str) -> Reference:
        return Reference(ref=f'{self.schema_prefix}{name}')

    def _get_unique_name(self, name: str) -> str:
        # TODO: Make sure it's enough.
        # A likely place to refactor later
        counter = 1
        original_name = name
        while name in self.schemas:
            name = f'{original_name}{counter}'
            counter += 1
        return name
