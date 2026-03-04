from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dmr.openapi.objects.encoding import Encoding
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.schema import Schema


@dataclass(kw_only=True)
class MediaType:
    """
    Media Type Object.

    Each Media Type Object provides schema and examples for the media
    type identified by its key.
    """

    schema: 'Reference | Schema'
    example: Any | None = None
    examples: dict[str, 'Example | Reference'] | None = None
    encoding: dict[str, 'Encoding'] | None = None
