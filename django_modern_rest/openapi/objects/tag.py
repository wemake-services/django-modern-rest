from dataclasses import dataclass
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.external_documentation import (
        ExternalDocumentation,
    )


@dataclass(frozen=True, kw_only=True, slots=True)
class Tag(BaseObject):
    """
    Adds metadata to a single tag that is used by the `Operation` object.

    It is not mandatory to have a `Tag` object per tag defined in the
    `Operation` object instances.
    """

    name: str
    description: str | None = None
    external_docs: 'ExternalDocumentation | None' = None
