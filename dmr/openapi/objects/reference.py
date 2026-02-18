from dataclasses import dataclass
from typing import final


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Reference:
    """
    A simple object to allow referencing other components in document.

    The `$ref` string value contains a URI RFC3986, which identifies
    the location of the value being referenced.
    """

    ref: str
    summary: str | None = None
    description: str | None = None
