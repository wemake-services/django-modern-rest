from dataclasses import dataclass
from typing import Any


@dataclass(kw_only=True, slots=True)
class ExternalDocumentation:
    """
    Allows referencing an external resource for extended documentation.

    .. versionchanged:: 0.16.0
        Added ``x_extensions`` for specification extensions.

    """

    url: str
    description: str | None = None
    #: Specification extensions, keys must start with ``x-``.
    x_extensions: dict[str, Any] | None = None
