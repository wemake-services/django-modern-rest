from typing import Any, ClassVar

import msgspec
from typing_extensions import override

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.plugins.msgspec.schema import MsgspecSchemaGenerator, SchemaHook


class Point:  # noqa: B903
    """Custom type that ``msgspec`` cannot describe natively."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


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

    @classmethod
    @override
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """Serialize ``Point`` objects, ``msgspec`` cannot do it natively."""
        if isinstance(to_serialize, Point):
            return {'x': to_serialize.x, 'y': to_serialize.y}
        return super().serialize_hook(to_serialize)


class Polygon(msgspec.Struct):
    points: list[Point]


class PolygonController(Controller[PointSerializer]):
    def get(self) -> Polygon:
        return Polygon(points=[Point(1, 2), Point(3, 4)])


# openapi: {"controller": "PolygonController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
