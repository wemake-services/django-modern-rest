from typing import TYPE_CHECKING, final

from django_modern_rest.openapi.objects import Reference

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.schema import Schema


@final
class SchemaRegistry:
    """
    Registry for OpenAPI Schema components.

    This registry collects and stores all reusable Schema objects that will
    be placed in the Components section of the OpenAPI specification.
    Schemas are registered by name and can be referenced throughout the spec.
    """

    def __init__(self) -> None:
        """Initialize an empty schema registry."""
        self._schemas: dict[str, Schema] = {}

    def register(self, name: str, schema: 'Schema | Reference') -> None:
        """Register a schema in the registry."""
        if isinstance(schema, Reference):
            # TODO: temporary skip. In future we must provide only `Schema`
            # type in function args.
            return

        # TODO: find another way to compare schemas.
        if name not in self._schemas:
            self._schemas[name] = schema

    def all(self) -> dict[str, 'Schema']:
        """Get all registered schemas."""
        return self._schemas

    def __contains__(self, name: str) -> bool:
        """Check if a schema name is in the registry."""
        return name in self._schemas


class OperationIdRegistry:
    """Registry for OpenAPI operation IDs."""

    def __init__(self) -> None:
        """Initialize an empty operation ids registry."""
        self.operation_ids: set[str] = set()

    def register(self, operation_id: str) -> None:
        """Register a operation ID in the registry."""
        # TODO: implement registration with constraint checks.
        raise NotImplementedError
