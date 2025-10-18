from dataclasses import dataclass
from typing import final

from django_modern_rest.openapi.objects.base import BaseObject


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class ServerVariable(BaseObject):
    """An object representing a `Server Variable` for server URL template."""

    default: str
    enum: list[str] | None = None
    description: str | None = None
