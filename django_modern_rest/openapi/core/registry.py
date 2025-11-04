from typing import TYPE_CHECKING, final

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

    def register(self, name: str, schema: 'Schema') -> None:
        """
        Register a schema in the registry.

        If a schema with the same name already exists, it will not be
        overwritten. This ensures idempotency and prevents accidental
        schema replacement.
        """
        if name not in self._schemas:
            self._schemas[name] = schema

    def all(self) -> dict[str, 'Schema']:
        """Get all registered schemas."""
        return self._schemas

    def __contains__(self, name: str) -> bool:
        """Check if a schema name is in the registry."""
        return name in self._schemas
