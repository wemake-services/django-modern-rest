from dataclasses import dataclass
from typing import TYPE_CHECKING

from dmr.openapi.core.builder import OperationIDBuilder
from dmr.openapi.core.merger import ConfigMerger
from dmr.openapi.core.registry import (
    OperationIdRegistry,
    SchemaRegistry,
    SecuritySchemeRegistry,
)
from dmr.openapi.generators import (
    ComponentGenerator,
    ComponentParserGenerator,
    ResponseGenerator,
    SchemaGenerator,
    SecuritySchemeGenerator,
)

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

    operation_id: OperationIDBuilder
    schema: SchemaGenerator
    component_parsers: ComponentParserGenerator
    response: ResponseGenerator
    component: ComponentGenerator
    security_scheme: SecuritySchemeGenerator


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
            operation_id=OperationIDBuilder(self),
            schema=SchemaGenerator(self),
            component_parsers=ComponentParserGenerator(self),
            response=ResponseGenerator(self),
            component=ComponentGenerator(self),
            security_scheme=SecuritySchemeGenerator(self),
        )
