import json
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.objects.openapi import ConvertedSchema
    from dmr.openapi.views.base import DumpedSchema, SchemaDumper


def _wrap_bytes_dumper(
    dumper: Callable[['ConvertedSchema'], bytes],
) -> 'SchemaDumper':
    """
    Wrap a bytes-returning JSON dumper to always return a UTF-8 string.

    This is used to normalize different JSON backends (e.g. `msgspec`)
    to a single `str`-based interface expected by `json_dumps`.
    """

    def wrapper(schema: 'ConvertedSchema') -> 'DumpedSchema':
        return dumper(schema).decode('utf-8')

    return wrapper


try:
    import msgspec
except ImportError:  # pragma: no cover
    _json_dumps: 'SchemaDumper' = json.dumps
else:
    _json_dumps = _wrap_bytes_dumper(msgspec.json.encode)


def json_dumps(schema: 'ConvertedSchema') -> 'DumpedSchema':
    """
    Serialize `ConvertedSchema` to decoded JSON string.

    Args:
        schema: Converted OpenAPI schema to be serialized.

    Returns:
        JSON string representation of the schema.

    """
    return _json_dumps(schema)
