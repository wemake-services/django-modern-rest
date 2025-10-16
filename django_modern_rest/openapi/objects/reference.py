from dataclasses import dataclass

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(frozen=True, kw_only=True, slots=True)
class Reference(BaseObject):
    """TODO: add docs."""

    ref: str
    summary: str | None = None
    description: str | None = None

    @property
    def value(self) -> str:
        """TODO: add docs."""
        return self.ref.split('/')[-1]
