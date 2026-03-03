from typing import ClassVar

from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema
from dmr.openapi.objects.security_scheme import (
    SecurityScheme,
)


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
    """Registry for ``Schemas``."""

    schema_prefix: ClassVar[str] = '#/components/schemas/'

    def __init__(self) -> None:
        """Initialize empty schema and type registers."""
        self.schemas: dict[str, Schema] = {}

    def register(
        self,
        schema_name: str,
        schema: Schema,
    ) -> Reference:
        """Register Schema in registry."""
        existing_schema = self.schemas.get(schema_name)
        if existing_schema:
            return self._make_reference(schema_name)

        self.schemas[schema_name] = schema
        return self._make_reference(schema_name)

    def get_reference(self, schema_name: str | None) -> Reference | None:
        """Get registered reference."""
        if schema_name and self.schemas.get(schema_name):
            return self._make_reference(schema_name)
        return None

    def maybe_resolve_reference(self, reference: Reference | Schema) -> Schema:
        """Resolve reference and return a schema back."""
        if isinstance(reference, Schema):
            return reference
        schema_name = reference.ref.removeprefix(self.schema_prefix)
        return self.schemas[schema_name]

    def _make_reference(self, name: str) -> Reference:
        return Reference(ref=f'{self.schema_prefix}{name}')


class SecuritySchemeRegistry:
    """Registry for ``SecuritySchemes``."""

    def __init__(self) -> None:
        """Initialize empty security schemes registry."""
        self.schemes: dict[str, SecurityScheme | Reference] = {}

    def register(
        self,
        name: str,
        scheme: SecurityScheme | Reference,
    ) -> None:
        """Register security scheme in registry."""
        self.schemes[name] = scheme
