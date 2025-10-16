from dataclasses import dataclass

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(frozen=True, kw_only=True, slots=True)
class XML(BaseObject):
    """TODO: add docs."""

    name: str | None = None
    namespace: str | None = None
    prefix: str | None = None
    attribute: bool = False
    wrapped: bool = False
