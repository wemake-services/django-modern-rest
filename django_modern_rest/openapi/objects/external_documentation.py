from dataclasses import dataclass

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(frozen=True, kw_only=True, slots=True)
class ExternalDocumentation(BaseObject):
    """TODO: add docs."""

    url: str
    description: str | None = None
