import dataclasses
from typing import Any, ClassVar, Protocol

from typing_extensions import Sentinel

from dmr.openapi.objects import Reference, Schema, SecurityScheme
from dmr.types import EMPTY


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
    ) -> Reference | Schema | None:
        """
        Resolve the annotation into schema or into a reference.

        Return ``None`` to fallback to the default resolution.
        """


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
    """Registry for ``Schemas``."""

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
        annotation: Any | Sentinel = EMPTY,
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
        resolution_context: dict[str, Schema] | None = None,
    ) -> Schema:
        """
        Resolve reference and return a flat schema back.

        Both a :class:`Reference` and a :class:`Schema` that carries
        a ``$ref`` point to a registered component. The schema's sibling
        keywords, like ``default``, only annotate that one usage:
        they are put on top of the component's own schema,
        but they never modify the component itself, #1491

        """
        if isinstance(reference, Schema):
            if reference.ref is None:
                return reference
            ref = reference.ref
        else:
            ref = reference.ref
        schema_name = ref.removeprefix(self.schema_prefix)
        target = (resolution_context or self.schemas)[schema_name]
        if isinstance(reference, Reference):
            return target
        return _overlay_ref_site(target, reference)

    def try_unregister(self, schema_name: str | None) -> None:
        """Try to unregister the schema by name."""
        if schema_name is not None:
            self._schemas.pop(schema_name, None)

    def _make_reference(self, name: str) -> Reference:
        return Reference(ref=f'{self.schema_prefix}{name}')


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
        self._schemes[name] = scheme


def _overlay_ref_site(target: Schema, ref_site: Schema) -> Schema:
    """
    Put the keywords next to ``$ref`` on top of the referenced schema.

    The component the ``$ref`` points to owns the actual shape,
    while the sibling keywords only annotate this one usage:
    non-empty sibling values win, and everything else stays untouched.
    """
    overrides: dict[str, Any] = {}
    for schema_field in dataclasses.fields(ref_site):
        if schema_field.name == 'ref':
            continue
        field_value = getattr(ref_site, schema_field.name)
        if field_value is None or field_value in ([], {}):
            continue
        overrides[schema_field.name] = field_value
    if not overrides:
        return target
    return dataclasses.replace(target, **overrides)


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
