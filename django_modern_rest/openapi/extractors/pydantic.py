from typing import Any, final, get_origin

import pydantic  # TODO: !!! Remove it !!!

from django_modern_rest.components import Body
from django_modern_rest.metadata import ComponentParserSpec
from django_modern_rest.openapi.extractors.base import BaseExtractor
from django_modern_rest.openapi.objects import (
    MediaType,
    RequestBody,
    Schema,
)


@final
class PydanticExtractor(BaseExtractor):
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
