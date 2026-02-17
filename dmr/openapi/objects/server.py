from dataclasses import dataclass
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from dmr.openapi.objects.server_variable import (
        ServerVariable,
    )


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Server:
    """An object representing a `Server`."""

    url: str
    description: str | None = None
    variables: 'dict[str, ServerVariable] | None' = None
