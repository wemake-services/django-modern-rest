from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dmr.openapi.objects.server_variable import ServerVariable


@dataclass(kw_only=True, slots=True)
class Server:
    """
    An object representing a `Server`.

    .. versionchanged:: 0.16.0
        Added ``name`` from OpenAPI 3.2.
        Added ``x_extensions`` for specification extensions.

    """

    url: str
    description: str | None = None
    variables: dict[str, 'ServerVariable'] | None = None

    # OpenAPI 3.2+ fields:
    name: str | None = None
    #: Specification extensions, keys must start with ``x-``.
    x_extensions: dict[str, Any] | None = None
