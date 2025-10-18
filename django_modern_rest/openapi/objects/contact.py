from dataclasses import dataclass

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(frozen=True, kw_only=True, slots=True)
class Contact(BaseObject):
    """Contact information for the exposed API."""

    name: str | None = None
    url: str | None = None
    email: str | None = None
