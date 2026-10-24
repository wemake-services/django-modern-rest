from typing import Any


def empty_serializer_context(endpoint: Any, controller: Any) -> dict[str, Any]:
    """It is always empty."""
    return {}
