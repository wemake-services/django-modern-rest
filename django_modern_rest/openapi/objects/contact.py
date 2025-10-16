from dataclasses import dataclass

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(frozen=True, kw_only=True, slots=True)
class Contact(BaseObject):
    """TODO: add docs."""

    name: str | None = None
    url: str | None = None
    email: str | None = None
