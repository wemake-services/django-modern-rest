from dataclasses import dataclass
from typing import TYPE_CHECKING, final

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.header import Header
    from django_modern_rest.openapi.objects.link import Link
    from django_modern_rest.openapi.objects.media_type import MediaType
    from django_modern_rest.openapi.objects.reference import Reference


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Response(BaseObject):
    """
    Describes a single response from an API Operation.

    Including design-time, static links to operations based on the response.
    """

    description: str
    headers: 'dict[str, Header | Reference] | None' = None
    content: 'dict[str, MediaType] | None' = None
    links: 'dict[str, Link | Reference] | None' = None
