from typing import Any, ClassVar

from typing_extensions import override

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.plugins.msgspec.schema import MsgspecSchemaGenerator, SchemaHook


class Point:  # noqa: B903
    """Custom type that ``msgspec`` cannot describe natively."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def point_schema(type_: type[Any]) -> dict[str, Any]:
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


class PointMsgspecSerializer(MsgspecSerializer):
    schema_generator = SchemaGenerator

    @classmethod
    @override
    def serialize_hook(cls, to_serialize: Any) -> Any:
        """Serialize ``Point`` objects, ``msgspec`` cannot do it natively."""
        if isinstance(to_serialize, Point):
            return {'x': to_serialize.x, 'y': to_serialize.y}
        return super().serialize_hook(to_serialize)

    @classmethod
    @override
    def deserialize_hook(
        cls,
        target_type: type[Any],
        to_deserialize: Any,
    ) -> Any:
        """Deserialize ``Point`` objects, ``msgspec`` cannot do it natively."""
        if target_type is Point:
            if isinstance(to_deserialize, Point):
                return to_deserialize
            return Point(to_deserialize['x'], to_deserialize['y'])
        return super().deserialize_hook(target_type, to_deserialize)


class PointsController(Controller[PointMsgspecSerializer]):
    def get(self) -> list[Point]:
        return [Point(1, 2), Point(3, 4)]


# run: {"controller": "PointsController", "method": "get", "url": "/api/points/"}  # noqa: ERA001, E501
# openapi: {"controller": "PointsController", "url": "/api/points/", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
