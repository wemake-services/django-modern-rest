from typing import Any, ClassVar

import pydantic
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode
from pydantic_core import CoreSchema
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.plugins.pydantic.schema import (
    JsonSchemaKwargs,
    PydanticSchemaGenerator,
)


class NoTitleJsonSchema(GenerateJsonSchema):
    """Drops ``title`` keys from the generated schemas."""

    @override
    def field_title_should_be_set(self, schema: Any) -> bool:
        """Do not generate titles for fields."""
        return False

    @override
    def generate(
        self,
        schema: CoreSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, Any]:
        """Generate a JSON schema and remove model titles from it."""
        json_schema = super().generate(schema, mode=mode)
        json_schema.pop('title', None)
        for component in json_schema.get('$defs', {}).values():
            component.pop('title', None)
        return json_schema


class SchemaGenerator(PydanticSchemaGenerator):
    json_schema_kwargs: ClassVar[JsonSchemaKwargs] = {
        'schema_generator': NoTitleJsonSchema,
    }


class PointPydanticSerializer(PydanticSerializer):
    schema_generator = SchemaGenerator


class Point(pydantic.BaseModel):
    coord_x: float
    coord_y: float


class PointsController(Controller[PointPydanticSerializer]):
    def get(self) -> list[Point]:
        return [Point(coord_x=1, coord_y=2), Point(coord_x=3, coord_y=4)]


# run: {"controller": "PointsController", "method": "get", "url": "/api/points/"}  # noqa: ERA001, E501
# openapi: {"controller": "PointsController", "url": "/api/points/", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
