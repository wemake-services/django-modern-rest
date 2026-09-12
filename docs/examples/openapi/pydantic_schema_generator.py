from collections.abc import Iterator
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
    def generate(
        self,
        schema: CoreSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, Any]:
        """Generate a JSON schema and remove all titles from it."""
        json_schema = super().generate(schema, mode=mode)
        return _drop_titles(json_schema)


def _drop_titles(json_schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove ``title`` keys from all nested schemas."""
    for subschema in _iter_nested(json_schema):
        subschema.pop('title', None)
    return json_schema


def _iter_nested(node: Any) -> Iterator[dict[str, Any]]:
    """Yield all dicts nested inside ``node``, including ``node`` itself."""
    if isinstance(node, dict):
        yield node
        yield from _iter_nested(list(node.values()))
    elif isinstance(node, list):
        for child in node:
            yield from _iter_nested(child)


class SchemaGenerator(PydanticSchemaGenerator):
    json_schema_kwargs: ClassVar[JsonSchemaKwargs] = {
        'schema_generator': NoTitleJsonSchema,
    }


class PointPydanticSerializer(PydanticSerializer):
    schema_generator = SchemaGenerator


class Point(pydantic.BaseModel):
    x: float
    y: float


class PointsController(Controller[PointPydanticSerializer]):
    def get(self) -> list[Point]:
        return [Point(x=1, y=2), Point(x=3, y=4)]


# run: {"controller": "PointsController", "method": "get", "url": "/api/points/"}  # noqa: ERA001, E501
# openapi: {"controller": "PointsController", "url": "/api/points/", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
