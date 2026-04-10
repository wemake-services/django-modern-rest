from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, get_origin

from dmr.openapi.core.merger import ConfigMerger
from dmr.openapi.core.registry import (
    OperationIdRegistry,
    SchemaCallback,
    SchemaRegistry,
    SecuritySchemeRegistry,
)
from dmr.openapi.generators import (
    ComponentParserGenerator,
    OperationIdGenerator,
    ParameterGenerator,
    ResponseGenerator,
    SchemaGenerator,
    SecuritySchemeGenerator,
)
from dmr.openapi.objects import Reference, Schema

if TYPE_CHECKING:
    from dmr.openapi.config import OpenAPIConfig


@dataclass(slots=True, frozen=True)
class RegistryContainer:
    """Container for registries."""

    operation_id: OperationIdRegistry
    schema: SchemaRegistry
    security_scheme: SecuritySchemeRegistry


@dataclass(slots=True, frozen=True)
class GeneratorContainer:
    """Container for generators."""

    operation_id: OperationIdGenerator
    schema: SchemaGenerator
    component_parsers: ComponentParserGenerator
    response: ResponseGenerator
    security_scheme: SecuritySchemeGenerator
    parameter: ParameterGenerator


class OpenAPIContext:
    """
    Context for OpenAPI specification generation.

    Maintains shared state and generators used across the OpenAPI
    generation process. Provides access to different generators.
    """

    def __init__(
        self,
        config: 'OpenAPIConfig',
    ) -> None:
        """Initialize the OpenAPI context."""
        self.config = config
        self.config_merger = ConfigMerger(self)

        # Initialize registries
        self.registries = RegistryContainer(
            operation_id=OperationIdRegistry(),
            schema=SchemaRegistry(),
            security_scheme=SecuritySchemeRegistry(),
        )

        # Initialize generators
        self.generators = GeneratorContainer(
            operation_id=OperationIdGenerator(self),
            schema=SchemaGenerator(self),
            component_parsers=ComponentParserGenerator(self),
            response=ResponseGenerator(self),
            security_scheme=SecuritySchemeGenerator(self),
            parameter=ParameterGenerator(self),
        )

    def register_schema(
        self,
        annotation: Any,
        schema: Schema | Reference | SchemaCallback,
        *,
        override: bool = False,
    ) -> None:
        """
        Register top-level annotation resolution into an OpenAPI schema.

        You can pass either a schema object itself, a reference, or a callback
        that returns schema, reference, or ``None`` to fallback
        to the default schema resolution process.

        .. warning::

            This only works for the top-level annotations with direct matches.
            For example: when you register ``User`` to have a specific schema,
            it will take effect only in cases where ``User`` is used directly.
            ``list[User]`` will use the default serializer
            schema resolution strategy.

        """
        real_type = get_origin(annotation) or annotation
        if not override and real_type in self.registries.schema.overrides:
            raise ValueError(f'{real_type} is already registered')
        self.registries.schema.overrides[real_type] = schema
