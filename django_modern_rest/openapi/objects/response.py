from dataclasses import dataclass
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.header import OpenAPIHeader
    from django_modern_rest.openapi.objects.link import Link
    from django_modern_rest.openapi.objects.media_type import MediaType
    from django_modern_rest.openapi.objects.reference import Reference


@dataclass(frozen=True, kw_only=True, slots=True)
class Response(BaseObject):
    """TODO: add docs."""

    description: str
    headers: 'dict[str, OpenAPIHeader | Reference] | None' = None
    content: 'dict[str, MediaType] | None' = None
    links: 'dict[str, Link | Reference] | None' = None
