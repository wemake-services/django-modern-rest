from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.objects.header import Header
    from dmr.openapi.objects.reference import Reference


@dataclass(kw_only=True, slots=True)
class Encoding:
    """A single encoding definition applied to a single schema property."""

    content_type: str | None = None
    headers: dict[str, 'Header | Reference'] | None = None
    style: str | None = None
    explode: bool | None = None
    allow_reserved: bool | None = None
