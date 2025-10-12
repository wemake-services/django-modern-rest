from collections.abc import Callable
from typing import Any

import ujson


def serialize(structure: Any, serialize_hook: Callable[[Any], Any]) -> str:
    """Serialize structure to JSON string using provided hook."""
    return ujson.dumps(structure, default=serialize_hook)


# TODO: fix a bug in `pustota` theme with `memoryview` annotation
def deserialize(buffer: bytes | bytearray | str) -> Any:
    """Deserialize JSON buffer to Python object."""
    return ujson.loads(buffer)
