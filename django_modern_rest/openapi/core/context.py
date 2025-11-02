from typing import TYPE_CHECKING, Any

from django_modern_rest.openapi.extractors.base import BaseExtractor
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
        self.collected_schemas: dict[str, Any] = {}  # For collecting $defs
        self.operation_generator = OperationGenerator(self)
        self.schema_extractors = BaseExtractor.get_extractors()

        # TODO: Looks like a hack. Can
        # Assign context to extractors so they can collect schemas
        for extractor in self.schema_extractors:
            if hasattr(extractor, 'context'):
                extractor.context = self  # pyright: ignore[reportAttributeAccessIssue]

    def collect_schema(self, name: str, schema: Any) -> None:
        """Collect a schema to be added to Components."""
        if name not in self.collected_schemas:
            self.collected_schemas[name] = schema

    def get_extractor(self, type_: Any) -> BaseExtractor:
        """Get extractor by given type."""
        for extractor in self.schema_extractors:
            if extractor.supports_type(type_):
                return extractor

        raise ValueError(f'No schema extractor found for type {type_}. ')
