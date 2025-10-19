from dataclasses import dataclass
from typing import final


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class ServerVariable:
    """An object representing a `Server Variable` for server URL template."""

    default: str
    enum: list[str] | None = None
    description: str | None = None
