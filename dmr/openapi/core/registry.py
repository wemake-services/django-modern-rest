from typing import Any, ClassVar, Protocol

from typing_extensions import Sentinel

from dmr.openapi.objects import (
    Components,
    Example,
    Parameter,
    Reference,
    RequestBody,
    Response,
    Schema,
    SecurityScheme,
)
from dmr.openapi.objects.openapi import normalize_key
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
    ) -> Schema | Reference | None:
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

    __slots__ = ('_schemas', 'overrides')

    schema_prefix: ClassVar[str] = '#/components/schemas/'

    def __init__(self) -> None:
        """Initialize empty schema and type registers."""
        self._schemas: dict[str, tuple[Schema, int | None]] = {}
        self.overrides: dict[Any, Schema | Reference | SchemaCallback] = {}

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
        """Resolve reference and return a schema back."""
        if isinstance(reference, Schema):
            return reference
        schema_name = reference.ref.removeprefix(self.schema_prefix)
        return (resolution_context or self.schemas)[schema_name]

    def try_unregister(self, schema_name: str | None) -> None:
        """Try to unregister the schema by name."""
        if schema_name is not None:
            self._schemas.pop(schema_name, None)

    def _make_reference(self, name: str) -> Reference:
        return Reference(ref=f'{self.schema_prefix}{name}')


class SecuritySchemeRegistry:
    """Registry for ``SecuritySchemes``."""

    __slots__ = ('schemes',)

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


class ComponentRegistry:
    """
    Registry for reusable components contributed from outside the pipeline.

    The framework derives schemas and security schemes from controllers on its
    own. Everything collected here comes from a description supplied by hand,
    the typical source being an adapted plain Django view whose path item
    references components the pipeline knows nothing about.
    """

    __slots__ = (
        'examples',
        'parameters',
        'request_bodies',
        'responses',
        'schemas',
    )

    #: Component categories that can be contributed, as field names.
    categories: ClassVar[tuple[str, ...]] = (
        'schemas',
        'responses',
        'parameters',
        'examples',
        'request_bodies',
    )

    def __init__(self) -> None:
        """Initialize empty registers for every contributed category."""
        self.schemas: dict[str, Schema] = {}
        self.responses: dict[str, Response | Reference] = {}
        # An OpenAPI category name, not a variable name we chose:
        self.parameters: dict[str, Parameter | Reference] = {}  # noqa: WPS110
        self.examples: dict[str, Example | Reference] = {}
        self.request_bodies: dict[str, RequestBody | Reference] = {}

    def contribute(self, components: Components) -> None:
        """
        Merge the given components into the registry.

        Contributing the very same definition twice is allowed, because one
        description is commonly shared by several adapted views.
        """
        for category in self.categories:
            self._merge(category, getattr(components, category) or {})

    def build(
        self,
        *,
        schemas: dict[str, Schema],
        security_schemes: dict[str, SecurityScheme | Reference],
    ) -> Components:
        """
        Build the ``components`` section of the document.

        Contributed schemas share the section with the ones the pipeline
        generates, so a name carrying both definitions is reported here.
        """
        for schema_name, generated in schemas.items():
            _check_conflict(
                'schemas',
                schema_name,
                self.schemas.get(schema_name),
                generated,
            )

        return Components(
            schemas=dict(sorted((self.schemas | schemas).items())),
            security_schemes=security_schemes,
            responses=self.responses or None,
            parameters=self.parameters or None,
            examples=self.examples or None,
            request_bodies=self.request_bodies or None,
        )

    def _merge(self, category: str, contributed: dict[str, Any]) -> None:
        registered: dict[str, Any] = getattr(self, category)
        for name, component in contributed.items():
            _check_conflict(category, name, registered.get(name), component)
            registered[name] = component


def _check_conflict(
    category: str,
    name: str,
    existing: Any | None,
    component: Any,
) -> None:
    if existing is not None and existing != component:
        raise ValueError(
            f'Component {name!r} is defined twice under '
            f'{normalize_key(category)!r} in the OpenAPI specification, '
            'with two different definitions. Components contributed by an '
            'adapted view share one document with the ones the framework '
            'generates, so rename the contribution or namespace it with the '
            '`component_prefix` argument of `adapt_django_view`.',
        )


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
