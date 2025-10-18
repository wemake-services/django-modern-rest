from dataclasses import dataclass
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.header import OpenAPIHeader
    from django_modern_rest.openapi.objects.reference import Reference


@dataclass(frozen=True, kw_only=True, slots=True)
class Encoding(BaseObject):
    """A single encoding definition applied to a single schema property."""

    content_type: str | None = None
    headers: 'dict[str, OpenAPIHeader | Reference] | None' = None
    style: str | None = None
    explode: bool = False
    allow_reserved: bool = False
