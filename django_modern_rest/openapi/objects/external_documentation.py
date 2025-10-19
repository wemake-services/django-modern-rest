from dataclasses import dataclass
from typing import final


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class ExternalDocumentation:
    """Allows referencing an external resource for extended documentation."""

    url: str
    description: str | None = None
