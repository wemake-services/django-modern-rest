from typing import TYPE_CHECKING, Any

from django_modern_rest.openapi.core.extractor import BaseSchemaExtractor
from django_modern_rest.openapi.generators.operation import OperationGenerator

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
        self._operation_ids: set[str] = set()

        # Initialize generators once with shared context:
        self.operation_generator = OperationGenerator(self)
        self.schema_extractors = BaseSchemaExtractor.get_extractors()

    def get_extractor(self, type_: Any) -> BaseSchemaExtractor:
        """Get extractor by given type."""
        for extractor in self.schema_extractors:
            if extractor.supports_type(type_):
                return extractor

        raise ValueError(f'No schema extractor found for type {type_}. ')
