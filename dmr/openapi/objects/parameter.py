from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

from dmr.internal.dataclass_aliases import Field

if TYPE_CHECKING:
    from dmr.openapi.objects.example import Example
    from dmr.openapi.objects.media_type import MediaType
    from dmr.openapi.objects.reference import Reference
    from dmr.openapi.objects.schema import Schema


@dataclass(unsafe_hash=True, kw_only=True, slots=True)
class ParameterMetadata:
    """Describes metadata for a single operation parameter."""

    description: str | None = None
    deprecated: bool = False
    allow_empty_value: bool | None = None
    style: str | None = None
    explode: bool | None = None
    allow_reserved: bool | None = None
    example: Any | None = None
    examples: dict[str, 'Example | Reference'] | None = None


@dataclass(kw_only=True, slots=True)
class Parameter(ParameterMetadata):
    """Describes a single operation parameter."""

    name: str
    param_in: Annotated[str, Field(alias='in')]
    schema: 'Reference | Schema | None' = None
    content: dict[str, 'MediaType'] | None = None
    required: bool = False
