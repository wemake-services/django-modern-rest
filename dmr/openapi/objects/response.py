from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.objects.header import Header
    from dmr.openapi.objects.link import Link
    from dmr.openapi.objects.media_type import MediaType
    from dmr.openapi.objects.reference import Reference


@dataclass(kw_only=True, slots=True)
class Response:
    """
    Describes a single response from an API Operation.

    Including design-time, static links to operations based on the response.

    .. versionchanged:: 0.16.0
        Added ``summary`` from OpenAPI 3.2.
        ``content`` values can now be references.

    """

    description: str | None = None
    headers: dict[str, 'Header | Reference'] | None = None
    content: dict[str, 'MediaType | Reference'] | None = None
    links: dict[str, 'Link | Reference'] | None = None

    # OpenAPI 3.2+ fields:
    #: Short label for the response, `description` is the long form.
    summary: str | None = None
