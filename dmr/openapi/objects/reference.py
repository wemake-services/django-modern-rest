from dataclasses import dataclass
from typing import Annotated

from dmr.internal.dataclass_aliases import Field


@dataclass(kw_only=True, slots=True)
class Reference:
    """
    A simple object to allow referencing other components in the document.

    The `$ref` string value contains a URI RFC3986, which identifies
    the location of the value being referenced.

    It is not used inside :class:`~dmr.openapi.objects.Schema` objects:
    since OpenAPI 3.1, ``$ref`` in a schema is a JSON Schema keyword,
    see ``Schema.ref``.

    .. versionchanged:: 0.16.0
        Not allowed in schema positions anymore, use ``Schema(ref=...)``.

    """

    ref: Annotated[str, Field(alias='$ref')]
    summary: str | None = None
    description: str | None = None
