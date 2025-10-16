from dataclasses import dataclass
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.external_documentation import (
        ExternalDocumentation,
    )


@dataclass(frozen=True, kw_only=True, slots=True)
class Tag(BaseObject):
    """TODO: add docs."""

    name: str
    description: str | None = None
    external_docs: 'ExternalDocumentation | None' = None
