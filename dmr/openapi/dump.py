from typing import TYPE_CHECKING

from dmr.internal.json import json_dumps as _json_dumps

if TYPE_CHECKING:
    from dmr.openapi.mappers.schema_normalization import DumpedSchema


def json_dumps(schema: 'DumpedSchema') -> str:
    """
    Serialize `DumpedSchema` to a decoded JSON string.

    Args:
        schema: Converted OpenAPI schema to be serialized.

    Returns:
        JSON string representation of the schema.

    .. versionadded:: 0.7.0
    .. versionchanged:: 0.15.0
        Renamed from ``json_dump`` to ``json_dumps``.
    """
    return _json_dumps(schema)


# Deprecated alias for backwards compatibility:
json_dump = json_dumps
