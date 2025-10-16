from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.server import Server


@dataclass(frozen=True, kw_only=True, slots=True)
class Link(BaseObject):
    """TODO: add docs."""

    operation_ref: str | None = None
    operation_id: str | None = None
    parameters: dict[str, Any] | None = None
    request_body: Any | None = None
    description: str | None = None
    server: 'Server | None' = None
