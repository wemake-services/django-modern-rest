from dataclasses import dataclass
from typing import Any


@dataclass(kw_only=True, slots=True)
class License:
    """
    License information for the exposed API.

    .. versionchanged:: 0.16.0
        Added ``x_extensions`` for specification extensions.

    """

    name: str
    identifier: str | None = None
    url: str | None = None
    #: Specification extensions, keys must start with ``x-``.
    x_extensions: dict[str, Any] | None = None
