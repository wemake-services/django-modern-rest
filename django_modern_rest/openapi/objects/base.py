from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, kw_only=True, slots=True)
class BaseObject:
    """Base class for schema spec objects."""

    def to_schema(self) -> dict[str, Any]:
        """TODO: adding docs."""
        return {'openapi': '3.1.0'}
