import abc
from collections.abc import Sequence
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias

from typing_extensions import override

from django_modern_rest.metadata import ComponentParserSpec
from django_modern_rest.openapi.objects import (
    OpenAPIType,
    Reference,
    RequestBody,
    Schema,
)

if TYPE_CHECKING:
    from django_modern_rest.openapi.core.context import OpenAPIContext


JSON_SCHEMA_TYPE_MAP: MappingProxyType[str, OpenAPIType] = MappingProxyType({
    'string': OpenAPIType.STRING,
    'number': OpenAPIType.NUMBER,
    'integer': OpenAPIType.INTEGER,
    'boolean': OpenAPIType.BOOLEAN,
    'array': OpenAPIType.ARRAY,
    'object': OpenAPIType.OBJECT,
    'null': OpenAPIType.NULL,
})

JSON_SCHEMA_FIELD_MAP: MappingProxyType[str, str] = MappingProxyType({
    'format': 'format',
    'title': 'title',
    'description': 'description',
    'default': 'default',
    'minimum': 'minimum',
    'maximum': 'maximum',
    'exclusiveMaximum': 'exclusive_maximum',
    'pattern': 'pattern',
    'enum': 'enum',
    'const': 'const',
    'example': 'example',
    'examples': 'examples',
    'required': 'required',
    'minLength': 'min_length',
    'maxLength': 'max_length',
    'minItems': 'min_items',
    'maxItems': 'max_items',
    'uniqueItems': 'unique_items',
    'multipleOf': 'multiple_of',
    'minProperties': 'min_properties',
    'maxProperties': 'max_properties',
    'deprecated': 'deprecated',
    'readOnly': 'read_only',
    'writeOnly': 'write_only',
})

_BaseSchemaExtractorRegistry: TypeAlias = list[type['BaseExtractor']]


class BaseExtractor:  # noqa: WPS214
    """
    Base class for extracting OpenAPI schemas from type annotations.

    Each serializer library (pydantic, msgspec, etc.) should implement
    this interface to convert their types into OpenAPI objects.

    Implementation approaches:
        1. For libraries with JSON Schema support (e.g., Pydantic):
           Generate JSON Schema dict and use _convert_json_schema() helper
        2. For libraries without JSON Schema support (e.g., dataclasses):
           Directly construct Schema/Reference objects in extract_schema()
    """

    _registry: ClassVar[_BaseSchemaExtractorRegistry] = []

    @override
    def __init_subclass__(cls) -> None:
        """Register subclasses schema extractors."""
        cls._registry.append(cls)

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Initialize extractor with OpenAPI context."""
        self.context = context

    @classmethod
    def get_extractors(
        cls,
        context: 'OpenAPIContext',
    ) -> Sequence['BaseExtractor']:
        """Get instances of all registered extractors with context."""
        return [extractor_cls(context) for extractor_cls in cls._registry]

    @abc.abstractmethod
    def extract_request_body(
        self,
        component_specs: list[ComponentParserSpec],
    ) -> RequestBody | None:
        """Extract RequestBody from component specifications."""
        raise NotImplementedError

    @abc.abstractmethod
    def extract_schema(self, type_: Any) -> Schema | Reference:
        """Extract OpenAPI Schema from a type annotation."""
        raise NotImplementedError

    @abc.abstractmethod
    def supports_type(self, type_: Any) -> bool:
        """Check if this extractor can handle the given type."""
        raise NotImplementedError

    # TODO: Extract other parts of schema

    def _convert_json_schema(
        self,
        json_schema: dict[str, Any],
    ) -> Schema | Reference:
        """
        Convert JSON Schema dict to OpenAPI Schema or Reference object.

        This is a helper method for extractors that work with libraries
        which can generate JSON Schema (e.g., Pydantic).

        Note: This method is optional. Extractors for libraries that don't
        provide JSON Schema generation (e.g., dataclasses, adaptix) should
        directly construct Schema/Reference objects in extract_schema().

        Args:
            json_schema: A JSON Schema dictionary conforming to JSON Schema spec

        Returns:
            OpenAPI Schema object or Reference to a schema component
        """
        ref = json_schema.get('$ref')
        if ref:
            return Reference(ref=ref)

        kwargs = self._extract_basic_fields(json_schema)
        kwargs.update(self._extract_complex_fields(json_schema))
        return Schema(**kwargs)

    def _extract_basic_fields(
        self,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}

        openapi_type = JSON_SCHEMA_TYPE_MAP.get(json_schema.get('type', ''))
        if openapi_type:
            fields['type'] = openapi_type

        for json_key, dataclass_field in JSON_SCHEMA_FIELD_MAP.items():
            field_value = json_schema.get(json_key)
            if field_value is not None:
                fields[dataclass_field] = field_value

        return fields

    def _extract_complex_fields(
        self,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        extracted_fields: dict[str, Any] = {}
        extracted_fields.update(self._extract_properties_field(json_schema))
        extracted_fields.update(self._extract_items_field(json_schema))
        extracted_fields.update(self._extract_combinators_fields(json_schema))
        return extracted_fields

    def _extract_properties_field(
        self,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        properties = json_schema.get('properties')
        if not properties:
            return {}
        return {
            'properties': {
                prop_key: self._convert_json_schema(prop_value)
                for prop_key, prop_value in properties.items()
            },
        }

    def _extract_items_field(
        self,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        schema_items = json_schema.get('items')
        if not schema_items:
            return {}
        return {'items': self._convert_json_schema(schema_items)}

    def _extract_combinators_fields(
        self,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}

        any_of_schemas = json_schema.get('anyOf')
        if any_of_schemas:
            fields['any_of'] = [
                self._convert_json_schema(schema) for schema in any_of_schemas
            ]

        all_of_schemas = json_schema.get('allOf')
        if all_of_schemas:
            fields['all_of'] = [
                self._convert_json_schema(schema) for schema in all_of_schemas
            ]

        return fields
