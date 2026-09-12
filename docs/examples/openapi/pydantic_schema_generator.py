from typing import Any, ClassVar

import pydantic
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import core_schema
from typing_extensions import override

from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.plugins.pydantic.schema import (
    JsonSchemaKwargs,
    PydanticSchemaGenerator,
)


class Point(pydantic.BaseModel):
    coord_x: float
    coord_y: float


class PointJsonSchema(GenerateJsonSchema):
    """Define the JSON schema for ``Point`` explicitly."""

    @override
    def model_schema(self, schema: core_schema.ModelSchema) -> dict[str, Any]:
        """Describe ``Point`` and use the default schema for other models."""
        if schema['cls'] is Point:
            return {
                'type': 'object',
                'properties': {
                    'coord_x': {'type': 'number'},
                    'coord_y': {'type': 'number'},
                },
                'required': ['coord_x', 'coord_y'],
            }
        return super().model_schema(schema)


class SchemaGenerator(PydanticSchemaGenerator):
    json_schema_kwargs: ClassVar[JsonSchemaKwargs] = {
        'schema_generator': PointJsonSchema,
    }


class PointPydanticSerializer(PydanticSerializer):
    schema_generator = SchemaGenerator


class PointsController(Controller[PointPydanticSerializer]):
    def get(self) -> list[Point]:
        return [Point(coord_x=1, coord_y=2), Point(coord_x=3, coord_y=4)]


# run: {"controller": "PointsController", "method": "get", "url": "/api/points/"}  # noqa: ERA001, E501
# openapi: {"controller": "PointsController", "url": "/api/points/", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
