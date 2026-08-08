from typing import TYPE_CHECKING

from dmr.internal.json import json_dump as _json_dump

if TYPE_CHECKING:
    from dmr.openapi.mappers.schema_normalization import DumpedSchema


def json_dump(schema: 'DumpedSchema') -> str:
    """
    Serialize `DumpedSchema` to a decoded JSON string.

    Args:
        schema: Converted OpenAPI schema to be serialized.

    Returns:
        JSON string representation of the schema.

    .. versionadded:: 0.7.0
    """
    return _json_dump(schema)
