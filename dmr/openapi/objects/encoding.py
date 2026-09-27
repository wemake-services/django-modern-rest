from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.objects.header import Header
    from dmr.openapi.objects.reference import Reference


@dataclass(kw_only=True, slots=True)
class Encoding:
    """
    A single encoding definition applied to a single schema property.

    .. versionchanged:: 0.16.0
        Added ``encoding``, ``item_encoding``, and ``prefix_encoding``
        from OpenAPI 3.2, they describe nested and sequential encodings.

    """

    content_type: str | None = None
    headers: dict[str, 'Header | Reference'] | None = None
    style: str | None = None
    explode: bool | None = None
    allow_reserved: bool | None = None

    # OpenAPI 3.2+ fields:
    # NOTE: `encoding` is mutually exclusive with the two below,
    # we let `openapi-spec-validator` report that.
    encoding: dict[str, 'Encoding'] | None = None
    item_encoding: 'Encoding | None' = None
    prefix_encoding: list['Encoding'] | None = None
