from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.encoding import Encoding
    from django_modern_rest.openapi.objects.example import Example
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.schema import Schema


@dataclass(frozen=True, kw_only=True, slots=True)
class OpenAPIMediaType(BaseObject):
    """TODO: add docs."""

    schema: 'Reference | Schema | None' = None
    example: Any | None = None
    examples: 'dict[str, Example | Reference] | None' = None
    encoding: 'dict[str, Encoding] | None' = None
