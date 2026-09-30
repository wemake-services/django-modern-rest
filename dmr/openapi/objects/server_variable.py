from dataclasses import dataclass
from typing import Any


@dataclass(kw_only=True, slots=True)
class ServerVariable:
    """
    An object representing a `Server Variable` for server URL template.

    .. versionchanged:: 0.16.0
        Added ``x_extensions`` for specification extensions.

    """

    default: str
    enum: list[str] | None = None
    description: str | None = None
    #: Specification extensions, keys must start with ``x-``.
    x_extensions: dict[str, Any] | None = None
