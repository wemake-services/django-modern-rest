from collections.abc import Callable
from typing import Any

import ujson


def serialize(structure: Any, serialize_hook: Callable[[Any], Any]) -> str:
    return ujson.dumps(structure, default=serialize_hook)


# TODO: fix a bug in `pustota` theme with `memoryview` annotation
def deserialize(buffer: bytes | bytearray | str) -> Any:
    return ujson.loads(buffer)
