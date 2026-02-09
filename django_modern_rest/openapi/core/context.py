from dataclasses import dataclass
from typing import TYPE_CHECKING

from django_modern_rest.openapi.core.merger import ConfigMerger
from django_modern_rest.openapi.core.registry import (
    OperationIdRegistry,
    SchemaRegistry,
)
from django_modern_rest.openapi.generators import (
    ComponentGenerator,
    OperationGenerator,
    OperationIDGenerator,
    ParameterGenerator,
    PathItemGenerator,
    RequestBodyGenerator,
    ResponseGenerator,
    SchemaGenerator,
)

if TYPE_CHECKING:
    from django_modern_rest.openapi.config import OpenAPIConfig


@dataclass(slots=True, frozen=True)
class RegistryContainer:
    """Container for registries."""

    operation_id: OperationIdRegistry
    schema: SchemaRegistry


@dataclass(slots=True, frozen=True)
class GeneratorContainer:
    """Container for generators."""

    operation: OperationGenerator
    operation_id: OperationIDGenerator
    schema: SchemaGenerator
    parameter: ParameterGenerator
    request_body: RequestBodyGenerator
    response: ResponseGenerator
    component: ComponentGenerator
    path_item: PathItemGenerator


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
        )

        # Initialize generators
        self.generators = GeneratorContainer(
            operation=OperationGenerator(self),
            operation_id=OperationIDGenerator(self),
            schema=SchemaGenerator(self),
            parameter=ParameterGenerator(self),
            request_body=RequestBodyGenerator(self),
            response=ResponseGenerator(self),
            component=ComponentGenerator(self),
            path_item=PathItemGenerator(self),
        )
