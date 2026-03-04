from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.media_type import MediaType
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.schema import Schema


@dataclass(frozen=True, kw_only=True, slots=True)
class ParameterMetadata:
    """Describes a metadata for a single operation parameter."""

    description: str | None = None
    deprecated: bool = False
    allow_empty_value: bool | None = None
    style: str | None = None
    explode: bool | None = None
    allow_reserved: bool | None = None
    example: Any | None = None
    examples: dict[str, 'Example | Reference'] | None = None


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Parameter(ParameterMetadata):
    """Describes a single operation parameter."""

    name: str
    param_in: str
    schema: 'Schema | Reference | None' = None
    content: dict[str, 'MediaType'] | None = None
    required: bool = False
