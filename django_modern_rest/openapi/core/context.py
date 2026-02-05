from dataclasses import dataclass
from typing import TYPE_CHECKING

from django_modern_rest.openapi.core.registry import (
    OperationIdRegistry,
    SchemaRegistry,
)
from django_modern_rest.openapi.generators.operation import (
    OperationGenerator,
    OperationIDGenerator,
)
from django_modern_rest.openapi.generators.parameter import ParameterGenerator
from django_modern_rest.openapi.generators.request_body import (
    RequestBodyGenerator,
)
from django_modern_rest.openapi.generators.response import ResponseGenerator
from django_modern_rest.openapi.generators.schema import SchemaGenerator

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

        # Initialize registries
        schema_registry = SchemaRegistry()
        self.registries = RegistryContainer(
            operation_id=OperationIdRegistry(),
            schema=schema_registry,
        )

        # Initialize generators
        self.generators = GeneratorContainer(
            operation=OperationGenerator(self),
            operation_id=OperationIDGenerator(self),
            schema=SchemaGenerator(schema_registry),
            parameter=ParameterGenerator(self),
            request_body=RequestBodyGenerator(self),
            response=ResponseGenerator(self),
        )
