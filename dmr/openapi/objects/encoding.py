from dataclasses import dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from dmr.openapi.objects.header import Header
    from dmr.openapi.objects.reference import Reference


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Encoding:
    """A single encoding definition applied to a single schema property."""

    content_type: str | None = None
    headers: 'dict[str, Header | Reference] | None' = None
    style: str | None = None
    explode: bool = False
    allow_reserved: bool = False
