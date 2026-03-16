from typing import Any, ClassVar, Protocol

from dmr.openapi.objects import Reference, Schema, SecurityScheme
from dmr.types import Empty, EmptyObj


class SchemaCallback(Protocol):
    """Callback protocol for the schema registration."""

    def __call__(
        self,
        annotation: Any,
        origin: Any,
        type_args: Any,
        *,
        used_for_response: bool,
        skip_registration: bool,
    ) -> Schema | Reference | None:
        """
        Resolve the annotation into schema or into a reference.

        Return ``None`` to fallback to the default resolution.
        """


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
        self._schemas: dict[str, tuple[Schema, int | None]] = {}
        self.overrides: dict[Any, Schema | Reference | SchemaCallback] = {}

    @property
    def schemas(self) -> dict[str, Schema]:
        """Return schemas by name."""
        return {
            schema_name: schema[0]
            for schema_name, schema in self._schemas.items()
        }

    def register(
        self,
        schema_name: str,
        schema: Schema,
        annotation: Any | Empty = EmptyObj,
    ) -> Reference:
        """Register Schema in registry."""
        existing_schema = self._schemas.get(schema_name)
        if existing_schema:
            _check_hashes(
                schema_name,
                annotation,
                existing_schema[1],
            )
            return self._make_reference(schema_name)

        self._schemas[schema_name] = (schema, _safe_hash(annotation))
        return self._make_reference(schema_name)

    def get_reference(
        self,
        schema_name: str | None,
        annotation: Any | Empty = EmptyObj,
    ) -> Reference | None:
        """Get registered reference."""
        if schema_name:
            existing_schema = self._schemas.get(schema_name)
            if existing_schema:
                _check_hashes(
                    schema_name,
                    annotation,
                    existing_schema[1],
                )
                return self._make_reference(schema_name)
        return None

    def maybe_resolve_reference(
        self,
        reference: Reference | Schema,
        *,
        resoltion_context: dict[str, Schema] | None = None,
    ) -> Schema:
        """Resolve reference and return a schema back."""
        if isinstance(reference, Schema):
            return reference
        schema_name = reference.ref.removeprefix(self.schema_prefix)
        return (resoltion_context or self.schemas)[schema_name]

    def try_unregister(self, schema_name: str | None) -> None:
        """Try to unregister the schema by name."""
        if schema_name is not None:
            self._schemas.pop(schema_name, None)

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


def _check_hashes(
    schema_name: str,
    annotation: Any | Empty,
    other_hash: int | None,
) -> None:
    if annotation is EmptyObj:
        return
    ann_hash = _safe_hash(annotation)
    if (
        ann_hash is not None
        and other_hash is not None
        and ann_hash != other_hash
    ):
        raise ValueError(
            f'Different schemas under a single name: {schema_name}',
        )


def _safe_hash(annotation: Any) -> int | None:
    if annotation is EmptyObj:
        return None
    try:
        return hash(annotation)
    except Exception:  # pragma: no cover
        return None
