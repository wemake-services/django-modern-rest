from dataclasses import dataclass
from typing import Annotated

from dmr.internal.dataclass_aliases import Field


@dataclass(kw_only=True, slots=True)
class Reference:
    """
    A simple object to allow referencing other components in the document.

    The `$ref` string value contains a URI RFC3986, which identifies
    the location of the value being referenced.
    """

    ref: Annotated[str, Field(alias='$ref')]
    summary: str | None = None
    description: str | None = None
