from typing import TYPE_CHECKING

from dmr.internal.json import json_dump as _json_dump

if TYPE_CHECKING:
    from dmr.openapi.objects.openapi import ConvertedSchema
    from dmr.openapi.views.base import DumpedSchema


def json_dump(schema: 'ConvertedSchema') -> 'DumpedSchema':
    """
    Serialize `ConvertedSchema` to a decoded JSON string.

    Args:
        schema: Converted OpenAPI schema to be serialized.

    Returns:
        JSON string representation of the schema.

    .. versionadded:: 0.7.0
    """
    return _json_dump(schema)
