import dataclasses
from typing import TYPE_CHECKING, Any, Literal

from dmr.openapi.objects import Parameter, ParameterMetadata, Reference, Schema

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class ParameterGenerator:
    """Generator for OpenAPI ``Parameter`` objects."""

    _context: 'OpenAPIContext'

    def __call__(
        self,
        model: Any,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
        *,
        param_in: Literal['query', 'path', 'cookie', 'header'],
    ) -> list[Parameter | Reference]:
        """Generate parameter spec for the OpenAPI."""
        # Import cycle:
        from dmr.metadata import get_annotated_metadata  # noqa: PLC0415

        schema = self._context.registries.schema.maybe_resolve_reference(
            self._context.generators.schema(
                model,
                serializer,
                skip_registration=True,
            ),
        )
        metadata = get_annotated_metadata(model, ParameterMetadata)
        return [  # pyright: ignore[reportReturnType]
            Parameter(
                name=property_name,
                param_in=param_in,
                schema=property_schema,
                required=property_name in schema.required,
                **self._compute_metadata(
                    metadata,
                    property_name,
                    property_schema,
                    schema,
                    self._context,
                ),
            )
            for property_name, property_schema in (
                schema.properties or {}
            ).items()
        ]

    def _compute_metadata(
        self,
        metadata: ParameterMetadata | None,
        property_name: str,
        property_schema: Schema | Reference,
        schema: Schema,
        context: 'OpenAPIContext',
    ) -> dict[str, Any]:
        metadata_params = (
            {}
            if metadata is None
            else {
                field.name: getattr(metadata, field.name)
                for field in dataclasses.fields(metadata)
            }
        )
        property_schema = context.registries.schema.maybe_resolve_reference(
            property_schema,
        )
        return {
            **metadata_params,
            'description': (
                property_schema.description
                or metadata_params.get('description')
                or schema.description
            ),
            'deprecated': (
                property_schema.deprecated
                or metadata_params.get('deprecated')
                or schema.deprecated
                or False
            ),
        }
