from dataclasses import dataclass
from typing import TYPE_CHECKING, final

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.server_variable import (
        ServerVariable,
    )


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Server(BaseObject):
    """An object representing a `Server`."""

    url: str
    description: str | None = None
    variables: 'dict[str, ServerVariable] | None' = None
