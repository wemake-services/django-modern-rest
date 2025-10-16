from dataclasses import dataclass

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(frozen=True, kw_only=True, slots=True)
class License(BaseObject):
    """TODO: add docs."""

    name: str
    identifier: str | None = None
    url: str | None = None
