from typing import Any

from django_modern_rest.openapi.core.registry import SchemaRegistry
from django_modern_rest.openapi.extractors.base import FieldExtractor
from django_modern_rest.openapi.objects.enums import OpenAPIType
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.schema import Schema
from django_modern_rest.openapi.types import FieldDefinition


class SchemaGenerator:
    """Generate FieldDefinition from dtos."""

    def __init__(self) -> None:
        """Init empty registry."""
        self.registry = SchemaRegistry()

    def generate(self, source_type: Any) -> Reference:
        """Get or creage Reference for source_type."""
        existing_ref = self.registry.get_reference(source_type)
        if existing_ref:
            return existing_ref

        extractor = self._find_extractor(source_type)

        field_definitions = extractor.extract_fields(source_type)

        props = {
            field_definition.name: self._make_schema(field_definition)
            for field_definition in field_definitions
        }

        schema = Schema(
            type=OpenAPIType.OBJECT,
            properties=props,
        )
        return self.registry.register(
            source_type=source_type,
            schema=schema,
            name=source_type.__name__,
        )

    def _find_extractor(self, source_type: Any) -> FieldExtractor[Any]:
        for extractor in FieldExtractor.registry:
            if extractor.is_supported(source_type):
                return extractor()
        raise ValueError(f'Field extractor for {source_type} not found')

    def _make_schema(
        self,
        field_definition: FieldDefinition,
    ) -> Schema | Reference:
        # TODO: Parse all from field_definition
        return Schema()
