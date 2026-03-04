from dataclasses import fields
from typing import Any, Literal

from dmr.metadata import get_annotated_metadata
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.objects.parameter import Parameter, ParameterMetadata
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema


def parameters_spec(
    model: Any,
    schema: Schema | Reference,
    context: OpenAPIContext,
    *,
    param_in: Literal['query', 'path', 'cookie', 'header'],
) -> list[Parameter | Reference]:
    """Generates ``Parameter`` specification for different components."""
    schema = context.registries.schema.maybe_resolve_reference(schema)
    metadata = get_annotated_metadata(model, ParameterMetadata)
    return [  # pyright: ignore[reportReturnType]
        Parameter(
            name=property_name,
            param_in=param_in,
            schema=property_schema,
            required=property_name in schema.required,
            **_compute_metadata(
                metadata,
                property_name,
                property_schema,
                schema,
                context,
            ),
        )
        for property_name, property_schema in (schema.properties or {}).items()
    ]


def _compute_metadata(
    metadata: ParameterMetadata | None,
    property_name: str,
    property_schema: Schema | Reference,
    schema: Schema,
    context: OpenAPIContext,
) -> dict[str, Any]:
    metadata_params = (
        {}
        if metadata is None
        else {
            field.name: getattr(metadata, field.name)
            for field in fields(metadata)
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
