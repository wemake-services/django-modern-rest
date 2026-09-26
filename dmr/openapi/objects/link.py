from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from dmr.internal.empty import EMPTY

if TYPE_CHECKING:
    from dmr.openapi.objects.server import Server


@dataclass(kw_only=True, slots=True)
class Link:
    """
    The Link object represents a possible design-time link for a response.

    The presence of a link does not guarantee the caller's ability
    to successfully invoke it, rather it provides a known relationship
    and traversal mechanism between responses and other operations.

    .. versionchanged:: 0.16.0
        ``request_body`` now defaults to :data:`~dmr.types.EMPTY`
        instead of ``None``, because ``None`` is a valid value for it.

    """

    operation_ref: str | None = None
    operation_id: str | None = None
    parameters: dict[str, Any] | None = None
    request_body: Any = EMPTY
    description: str | None = None
    server: 'Server | None' = None
