from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.example import Example
    from django_modern_rest.openapi.objects.media_type import OpenAPIMediaType
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.schema import Schema


@dataclass(frozen=True, kw_only=True, slots=True)
class OpenAPIHeader(BaseObject):
    """TODO: add docs."""

    schema: 'Schema | Reference | None' = None
    name: Literal[''] = ''
    param_in: Literal['header'] = 'header'
    description: str | None = None
    required: bool = False
    deprecated: bool = False
    style: str | None = None
    explode: bool | None = None
    example: Any | None = None
    examples: 'dict[str, Example | Reference] | None' = None
    content: 'dict[str, OpenAPIMediaType] | None' = None

    @property
    def _exclude_fields(self) -> set[str]:
        return {'name', 'param_in'}
