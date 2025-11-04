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

    The registry ensures that each schema is registered only once, preventing
    duplicates and maintaining a single source of truth for all schema definitions.

    Note: Only Schema objects are stored in the registry, not References.
    References are used elsewhere in the spec to point to schemas in this registry.
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

    def get(self, name: str) -> 'Schema | None':
        """Retrieve a schema from the registry by name."""
        return self._schemas.get(name)

    def all(self) -> dict[str, 'Schema']:
        """Get all registered schemas."""
        return self._schemas.copy()

    def clear(self) -> None:
        """Clear all registered schemas from the registry."""
        self._schemas.clear()

    def __len__(self) -> int:
        """Return the number of registered schemas."""
        return len(self._schemas)

    def __contains__(self, name: str) -> bool:
        """Check if a schema name is in the registry."""
        return name in self._schemas
