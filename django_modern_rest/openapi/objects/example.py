from dataclasses import dataclass
from typing import Any

from django_modern_rest.openapi.objects.base import BaseObject


@dataclass(frozen=True, kw_only=True, slots=True)
class Example(BaseObject):
    """TODO: add docs."""

    id: str | None = None
    summary: str | None = None
    description: str | None = None
    value: Any | None = None
    external_value: str | None = None
