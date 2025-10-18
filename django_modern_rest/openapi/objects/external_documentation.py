from dataclasses import dataclass
from typing import final

from django_modern_rest.openapi.objects.base import BaseObject


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class ExternalDocumentation(BaseObject):
    """Allows referencing an external resource for extended documentation."""

    url: str
    description: str | None = None
