from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.server import Server


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Link:
    """
    The Link object represents a possible design-time link for a response.

    The presence of a link does not guarantee the caller's ability
    to successfully invoke it, rather it provides a known relationship
    and traversal mechanism between responses and other operations.
    """

    operation_ref: str | None = None
    operation_id: str | None = None
    parameters: dict[str, Any] | None = None
    request_body: Any | None = None
    description: str | None = None
    server: 'Server | None' = None
