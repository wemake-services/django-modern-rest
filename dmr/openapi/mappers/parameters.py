from typing import TYPE_CHECKING, Literal

from dmr.metadata import EndpointMetadata
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.objects.parameter import Parameter
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer


def parameters_spec(
    schema: Schema | Reference,
    serializer: type['BaseSerializer'],
    metadata: EndpointMetadata,
    context: OpenAPIContext,
    *,
    param_in: Literal['query', 'path', 'cookie', 'header'],
) -> list[Parameter | Reference]:
    """Generates ``Parameter`` specification for different components."""
    schema = context.registries.schema.maybe_resolve_reference(schema)
    return [
        Parameter(
            name=property_name,
            param_in=param_in,
            schema=property_schema,
            required=property_name in schema.required,
            description=schema.description,
            deprecated=schema.deprecated or False,
            # TODO: add `Annotated[Query[QueryModel], ParameterMetadata()]`
            # support for all components
        )
        for property_name, property_schema in (schema.properties or {}).items()
    ]
