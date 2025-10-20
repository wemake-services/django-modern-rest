from dataclasses import dataclass
from typing import final


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Contact:
    """Contact information for the exposed API."""

    name: str | None = None
    url: str | None = None
    email: str | None = None
