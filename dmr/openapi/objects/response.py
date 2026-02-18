from dataclasses import dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from dmr.openapi.objects.header import Header
    from dmr.openapi.objects.link import Link
    from dmr.openapi.objects.media_type import MediaType
    from dmr.openapi.objects.reference import Reference


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Response:
    """
    Describes a single response from an API Operation.

    Including design-time, static links to operations based on the response.
    """

    description: str
    headers: 'dict[str, Header | Reference] | None' = None
    content: 'dict[str, MediaType] | None' = None
    links: 'dict[str, Link | Reference] | None' = None
