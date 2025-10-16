from dataclasses import dataclass

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(unsafe_hash=True, frozen=True, kw_only=True, slots=True)
class Discriminator(BaseObject):
    """TODO: add docs."""

    property_name: str
    mapping: dict[str, str] | None = None
