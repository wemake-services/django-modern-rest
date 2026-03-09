from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dmr.openapi.objects.encoding import Encoding
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.schema import Schema


@dataclass(kw_only=True, slots=True)
class MediaType:
    """
    Media Type Object.

    Each Media Type Object provides schema and examples for the media
    type identified by its key.
    """

    # Can be `None` only when `item_schema` is set:
    schema: 'Reference | Schema | None' = None
    example: Any | None = None
    examples: dict[str, 'Example | Reference'] | None = None
    encoding: dict[str, 'Encoding'] | None = None

    # OpenAPI 3.2+ fields:
    item_schema: 'Reference | Schema | None' = None
    item_encoding: 'Encoding | None' = None
    prefix_encoding: 'Encoding | None' = None

    def __post_init__(self) -> None:
        if self.schema is None and self.item_schema is None:
            raise ValueError('Both `schema` and `item_schema` cannot be None')
