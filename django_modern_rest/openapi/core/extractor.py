from collections.abc import Sequence
from types import MappingProxyType
from typing import Any, ClassVar, TypeAlias, final, get_origin

import pydantic  # TODO: !!! Remove it !!!

from django_modern_rest.components import Body
from django_modern_rest.metadata import ComponentParserSpec
from django_modern_rest.openapi.objects import (
    MediaType,
    OpenAPIType,
    RequestBody,
    Schema,
)

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

_BaseSchemaExtractorRegistry: TypeAlias = list[type['BaseSchemaExtractor']]


class BaseSchemaExtractor:  # noqa: WPS214
    """
    Base class for extracting OpenAPI schemas from type annotations.

    Each serializer library (pydantic, msgspec, etc.) should implement
    this interface to convert their types into OpenAPI objects.
    """

    _registry: ClassVar[_BaseSchemaExtractorRegistry] = []

    def __init_subclass__(cls) -> None:
        """Register subclasses schema extractors."""
        cls._registry.append(cls)

    @classmethod
    def get_extractors(cls) -> Sequence['BaseSchemaExtractor']:
        """Get instances of all registered extractors."""
        return [extractor_cls() for extractor_cls in cls._registry]

    def extract_request_body(
        self,
        component_specs: list[ComponentParserSpec],
    ) -> RequestBody | None:
        """Extract RequestBody from component specifications."""
        raise NotImplementedError

    def extract_schema(self, type_: Any) -> Schema:
        """Extract OpenAPI Schema from a type annotation."""
        raise NotImplementedError

    def supports_type(self, type_: Any) -> bool:
        """Check if this extractor can handle the given type."""
        raise NotImplementedError

    # TODO: Extract other parts of schema

    def _convert_json_schema(self, json_schema: dict[str, Any]) -> Schema:
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


@final
class PydanticSchemaExtractor(BaseSchemaExtractor):
    """OpenAPI schema extractor for Pydantic models."""

    def supports_type(self, type_: Any) -> bool:
        """Check if this extractor can handle the given type."""
        # TODO: complex checks?
        return issubclass(type_, pydantic.BaseModel)

    def extract_request_body(
        self,
        component_specs: list[ComponentParserSpec],
    ) -> RequestBody | None:
        """Extract RequestBody from Body component."""
        for component_cls, type_args in component_specs:
            origin = get_origin(component_cls) or component_cls
            if issubclass(origin, Body):
                body_type = type_args[0]
                return RequestBody(
                    content={
                        'application/json': self._extract_media_type(body_type),
                    },
                    required=True,
                )
        return None

    def extract_schema(self, type_: Any) -> Schema:
        """Extract OpenAPI Schema from pydantic type."""
        adapter = pydantic.TypeAdapter(type_)
        json_schema = adapter.json_schema(mode='serialization')
        return self._convert_json_schema(json_schema)

    # TODO: Extract other parts of schema

    def _extract_media_type(self, type_: Any) -> MediaType:
        """Extract MediaType with schema."""
        return MediaType(schema=self.extract_schema(type_))
