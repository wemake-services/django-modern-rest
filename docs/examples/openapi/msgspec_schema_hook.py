from typing import Any, ClassVar

import msgspec

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.plugins.msgspec.schema import MsgspecSchemaGenerator, SchemaHook


class Point:
    """Custom type that ``msgspec`` cannot describe natively."""


def point_schema(type_: type) -> dict[str, Any]:
    """Generate JSON schemas for custom types."""
    if type_ is Point:
        return {
            'type': 'object',
            'properties': {
                'x': {'type': 'number'},
                'y': {'type': 'number'},
            },
            'required': ['x', 'y'],
        }
    raise NotImplementedError(type_)


class SchemaGenerator(MsgspecSchemaGenerator):
    schema_hook: ClassVar[SchemaHook | None] = point_schema


class PointSerializer(MsgspecSerializer):
    schema_generator = SchemaGenerator


class Polygon(msgspec.Struct):
    points: list[Point]


class PolygonController(Controller[PointSerializer]):
    def get(self) -> Polygon:
        return Polygon(points=[Point(), Point()])


# openapi: {"controller": "PolygonController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
