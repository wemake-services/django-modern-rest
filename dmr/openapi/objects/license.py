from dataclasses import dataclass
from typing import final


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class License:
    """License information for the exposed API."""

    name: str
    identifier: str | None = None
    url: str | None = None
