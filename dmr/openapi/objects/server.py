from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.objects.server_variable import ServerVariable


@dataclass(kw_only=True, slots=True)
class Server:
    """
    An object representing a `Server`.

    .. versionchanged:: 0.16.0
        Added ``name`` from OpenAPI 3.2.

    """

    url: str
    description: str | None = None
    variables: dict[str, 'ServerVariable'] | None = None

    # OpenAPI 3.2+ fields:
    name: str | None = None
