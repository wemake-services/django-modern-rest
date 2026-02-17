from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.example import Example
    from django_modern_rest.openapi.objects.media_type import MediaType
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.schema import Schema


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Header:
    """
    Header Object.

    The Header Object follows the structure of the Parameter Object
    with the following changes:
    All traits that are affected by the location MUST be applicable to
    a location of header (for example, style).
    """

    schema: 'Schema | Reference | None' = None
    description: str | None = None
    required: bool | None = None
    deprecated: bool | None = None
    style: str | None = None
    explode: bool | None = None
    example: Any | None = None
    examples: 'dict[str, Example | Reference] | None' = None
    content: 'dict[str, MediaType] | None' = None
