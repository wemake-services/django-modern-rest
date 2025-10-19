from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.encoding import Encoding
    from django_modern_rest.openapi.objects.example import Example
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.schema import Schema


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class MediaType:
    """
    Media Type Object.

    Each Media Type Object provides schema and examples for the media
    type identified by its key.
    """

    schema: 'Reference | Schema | None' = None
    example: Any | None = None
    examples: 'dict[str, Example | Reference] | None' = None
    encoding: 'dict[str, Encoding] | None' = None
