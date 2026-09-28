import dataclasses
from typing import Any, ClassVar

from typing_extensions import Sentinel

from dmr.internal.types import EMPTY
from dmr.openapi.objects import Reference, Schema, SecurityScheme


class OperationIdRegistry:
    """Registry for OpenAPI operation IDs."""

    __slots__ = ('_operation_ids',)

    def __init__(self) -> None:
        """Initialize an empty operation ID registry."""
        self._operation_ids: set[str] = set()

    def register(self, operation_id: str) -> None:
        """Register an operation ID in the registry."""
        if operation_id in self._operation_ids:
            raise ValueError(
                f'Operation ID {operation_id!r} is already registered in the '
                'OpenAPI specification. Operation IDs must be unique across '
                'all endpoints to ensure proper API documentation. '
                'Please use a different operation ID for this endpoint.',
            )

        self._operation_ids.add(operation_id)


class SchemaRegistry:
    """
    Registry for ``Schemas``.

    .. versionchanged:: 0.16.0
        Removed ``try_unregister``: components are now registered
        only when the final schema references them,
        see :meth:`dmr.openapi.generators.SchemaGenerator.register`.
        References to schemas are now :class:`~dmr.openapi.objects.Schema`
        objects with ``$ref`` set, not ``Reference`` objects,
        because OpenAPI 3.1 defines ``$ref`` as a JSON Schema keyword.

    """

    __slots__ = ('_schemas',)

    schema_prefix: ClassVar[str] = '#/components/schemas/'

    def __init__(self) -> None:
        """Initialize empty schema and type registers."""
        self._schemas: dict[str, tuple[Schema, int | None]] = {}

    @property
    def schemas(self) -> dict[str, Schema]:
        """Return schemas by name."""
        return {
            schema_name: self._schemas[schema_name][0]
            for schema_name in sorted(self._schemas)
        }

    def register(
        self,
        schema_name: str,
        schema: Schema,
        annotation: Any | Sentinel = EMPTY,
    ) -> Schema:
        """Register Schema in registry, return a reference to it."""
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
        annotation: Any | Sentinel = EMPTY,
    ) -> Schema | None:
        """Get a reference to the registered schema, if it exists."""
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
        reference: Schema,
        *,
        resolution_context: dict[str, Schema] | None = None,
    ) -> Schema:
        """
        Resolve a schema with ``$ref`` and return the referenced schema back.

        Schemas without ``$ref`` are returned as is.
        *resolution_context* holds components that are not registered yet,
        they are checked before the registered ones.

        The keywords next to ``$ref``, like ``default``, only annotate
        that one usage: they are put on top of the component's own schema,
        but they never modify the component itself, #1491

        .. versionchanged:: 0.16.0
            Falls back to the registered schemas
            when *resolution_context* does not have the component.
            Accepts only ``Schema`` objects.
            Keywords next to ``$ref`` are kept in the result.

        """
        if reference.ref is None:
            return reference
        schema_name = reference.ref.removeprefix(self.schema_prefix)
        if resolution_context and schema_name in resolution_context:
            target = resolution_context[schema_name]
        else:
            target = self._schemas[schema_name][0]
        return _overlay_ref_site(target, reference)

    def _make_reference(self, name: str) -> Schema:
        return Schema(ref=f'{self.schema_prefix}{name}')


class SecuritySchemeRegistry:
    """
    Registry for ``SecuritySchemes``.

    .. versionchanged:: 0.16.0
        ``schemes`` is now a property that returns
        security schemes sorted by name.

    """

    __slots__ = ('_schemes',)

    def __init__(self) -> None:
        """Initialize empty security schemes registry."""
        self._schemes: dict[str, SecurityScheme | Reference] = {}

    @property
    def schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Return security schemes by name."""
        return {
            scheme_name: self._schemes[scheme_name]
            for scheme_name in sorted(self._schemes)
        }

    def register(
        self,
        name: str,
        scheme: SecurityScheme | Reference,
    ) -> None:
        """Register security scheme in registry."""
        existing = self._schemes.get(name)
        if existing is not None:
            if existing != scheme:
                raise ValueError(
                    f'Security scheme {name!r} is already registered in the '
                    'OpenAPI specification. Security scheme names must be '
                    'unique. Re-registering the same name with a different '
                    'scheme is not allowed.',
                )
            return

        self._schemes[name] = scheme


def _overlay_ref_site(target: Schema, ref_site: Schema) -> Schema:
    """
    Put the keywords next to ``$ref`` on top of the referenced schema.

    The component the ``$ref`` points to owns the actual shape,
    while the sibling keywords only annotate this one usage:
    set sibling values win, and everything else stays untouched.
    """
    sibling_values = {
        schema_field.name: field_value
        for schema_field in dataclasses.fields(ref_site)
        if (field_value := _is_sibling_set(ref_site, schema_field)) is not EMPTY
    }
    if not sibling_values:
        return target
    return dataclasses.replace(target, **sibling_values)  # type: ignore[arg-type]


def _is_sibling_set(
    ref_site: Schema,
    schema_field: dataclasses.Field[Any],
) -> Any | Sentinel:
    """Check that a keyword next to ``$ref`` is really set on the schema."""
    field_value = getattr(ref_site, schema_field.name)
    # Ignore fields with default values and `ref` itself:
    if (
        schema_field.name == 'ref'
        or field_value == schema_field.default
        or (
            schema_field.default_factory is not dataclasses.MISSING
            and field_value == schema_field.default_factory()
        )
    ):
        return EMPTY
    return field_value


def _check_hashes(
    schema_name: str,
    annotation: Any | Sentinel,
    other_hash: int | None,
) -> None:
    if annotation is EMPTY:
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
    if annotation is EMPTY:
        return None
    try:
        return hash(annotation)
    except Exception:  # pragma: no cover
        return None
