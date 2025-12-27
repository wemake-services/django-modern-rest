from typing import TYPE_CHECKING, Any

from django_modern_rest.openapi.core.registry import (
    OperationIdRegistry,
    SchemaRegistry,
)
from django_modern_rest.openapi.extractors.base import BaseExtractor
from django_modern_rest.openapi.generators.operation import (
    OperationGenerator,
    OperationIDGenerator,
)

if TYPE_CHECKING:
    from django_modern_rest.openapi.config import OpenAPIConfig


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

        # Initialize registry and generators:
        self.schema_registry = SchemaRegistry()
        self.operation_id_registry = OperationIdRegistry()
        self.operation_generator = OperationGenerator(self)
        self.operation_id_generator = OperationIDGenerator(self)
        self.schema_extractors = BaseExtractor.all(self)

    def get_extractor(self, type_: Any) -> BaseExtractor:
        """Get extractor by given type."""
        for extractor in self.schema_extractors:
            if extractor.supports_type(type_):
                return extractor

        raise ValueError(f'No schema extractor found for type {type_}.')
