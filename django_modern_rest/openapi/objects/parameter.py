from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.example import Example
    from django_modern_rest.openapi.objects.media_type import MediaType
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.schema import Schema


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Parameter:
    """Describes a single operation parameter."""

    name: str
    param_in: str
    schema: 'Schema | Reference | None' = None
    description: str | None = None
    required: bool = False
    deprecated: bool = False
    allow_empty_value: bool = False
    style: str | None = None
    explode: bool | None = None
    allow_reserved: bool = False
    example: Any | None = None
    examples: 'Mapping[str, Example | Reference] | None' = None
    content: 'dict[str, MediaType] | None' = None
