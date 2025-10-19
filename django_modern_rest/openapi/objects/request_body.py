from dataclasses import dataclass
from typing import TYPE_CHECKING, final

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.media_type import MediaType


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class RequestBody(BaseObject):
    """Describes a single request body."""

    content: 'dict[str, MediaType]'
    description: str | None = None
    required: bool = False
