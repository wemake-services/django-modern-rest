from dataclasses import dataclass
from typing import Any, final


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Example:
    """
    Example Object.

    In all cases, the example value is expected to be compatible with the
    type schema of its associated value. Tooling implementations MAY choose
    to validate compatibility automatically, and reject the example
    value(s) if incompatible.
    """

    id: str | None = None
    summary: str | None = None
    description: str | None = None
    value: Any | None = None
    external_value: str | None = None
