from dataclasses import dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.media_type import MediaType


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class RequestBody:
    """Describes a single request body."""

    content: 'dict[str, MediaType]'
    description: str | None = None
    required: bool = False
