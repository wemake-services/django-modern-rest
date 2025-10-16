from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.example import Example
    from django_modern_rest.openapi.objects.media_type import OpenAPIMediaType
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.schema import Schema


@dataclass(frozen=True, kw_only=True, slots=True)
class Parameter(BaseObject):
    """TODO: add docs."""

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
    content: 'dict[str, OpenAPIMediaType] | None' = None

    @property
    def _exclude_fields(self) -> set[str]:
        exclude: set[str] = set()
        if self.param_in != 'query':
            # these are only allowed in query params
            exclude.update({'allow_empty_value', 'allow_reserved'})

        return exclude
