from typing import TYPE_CHECKING, Any

from django_modern_rest.openapi.core.registry import SchemaRegistry
from django_modern_rest.openapi.extractors.base import BaseExtractor
from django_modern_rest.openapi.generators.operation import OperationGenerator
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.schema import Schema

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

        # Initialize registry and generators:
        self.schema_registry = SchemaRegistry()
        self.operation_generator = OperationGenerator(self)
        self.schema_extractors = BaseExtractor.get_extractors(self)

    def collect_schema(self, name: str, schema: Any) -> None:
        """
        Collect a schema to be added to Components.

        This is a convenience method that delegates to the schema registry.
        It's kept for backward compatibility with existing extractors.

        Args:
            name: The name/identifier for the schema
            schema: The Schema object to register .Reference objects are not
                    registered, as they point to schemas already in the registry

        Raises:
            TypeError: If schema is a Reference object or not a Schema object
        """
        if isinstance(schema, Reference):
            raise TypeError(
                f'Cannot register Reference object as schema. '
                f'References point to schemas in the registry, they are not '
                f'registered themselves. Schema name: {name!r}',
            )

        if not isinstance(schema, Schema):
            raise TypeError(
                f'Expected Schema object, got {type(schema).__name__}. '
                f'Schema name: {name!r}',
            )

        self.schema_registry.register(name, schema)

    def get_extractor(self, type_: Any) -> BaseExtractor:
        """Get extractor by given type."""
        for extractor in self.schema_extractors:
            if extractor.supports_type(type_):
                return extractor

        raise ValueError(f'No schema extractor found for type {type_}. ')
