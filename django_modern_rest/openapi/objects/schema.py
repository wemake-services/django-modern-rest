from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from django_modern_rest.openapi.objects.base import BaseObject

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.discriminator import Discriminator
    from django_modern_rest.openapi.objects.enums import (
        OpenAPIFormat,
        OpenAPIType,
    )
    from django_modern_rest.openapi.objects.external_documentation import (
        ExternalDocumentation,
    )
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.xml import XML


@dataclass(frozen=True, kw_only=True, slots=True)
class Schema(BaseObject):
    """TODO: add docs."""

    all_of: 'Sequence[Reference | Schema] | None' = field(
        default=None,
    )
    any_of: 'Sequence[Reference | Schema] | None' = field(
        default=None,
    )
    schema_not: 'Reference | Schema | None' = field(
        default=None,
    )
    schema_if: 'Reference | Schema | None' = field(
        default=None,
    )
    then: 'Reference | Schema | None' = None
    schema_else: 'Reference | Schema | None' = field(
        default=None,
    )
    dependent_schemas: 'dict[str, Reference | Schema] | None' = field(
        default=None,
    )
    prefix_items: 'Sequence[Reference | Schema] | None' = field(
        default=None,
    )
    items: 'Reference | Schema | None' = None
    contains: 'Reference | Schema | None' = None
    properties: 'dict[str, Reference | Schema] | None' = None
    pattern_properties: 'dict[str, Reference | Schema] | None' = field(
        default=None,
    )
    additional_properties: 'Reference | Schema | bool | None' = field(
        default=None,
    )
    property_names: 'Reference | Schema | None' = field(
        default=None,
    )
    unevaluated_items: 'Reference | Schema | None' = field(
        default=None,
    )
    unevaluated_properties: 'Reference | Schema | None' = field(
        default=None,
    )
    type: 'OpenAPIType | Sequence[OpenAPIType] | None' = None
    enum: Sequence[Any] | None = None
    const: Any | None = None
    multiple_of: float | None = field(
        default=None,
    )
    maximum: float | None = None
    exclusive_maximum: float | None = None
    minimum: float | None = None
    max_length: int | None = field(
        default=None,
    )
    min_length: int | None = field(
        default=None,
    )
    pattern: str | None = None
    max_items: int | None = field(
        default=None,
    )
    min_items: int | None = field(default=None, metadata={'alias': 'minItems'})
    unique_items: bool | None = field(
        default=None,
    )
    max_contains: int | None = field(
        default=None,
    )
    min_contains: int | None = field(
        default=None,
    )
    max_properties: int | None = field(
        default=None,
    )
    min_properties: int | None = field(
        default=None,
    )
    required: Sequence[str] | None = None
    dependent_required: dict[str, Sequence[str]] | None = field(
        default=None,
    )
    format: 'OpenAPIFormat | None' = None
    content_encoding: str | None = field(
        default=None,
    )
    content_media_type: str | None = field(
        default=None,
    )
    content_schema: 'Reference | Schema | None' = field(
        default=None,
    )
    title: str | None = None
    description: str | None = None
    default: Any | None = None
    deprecated: bool | None = None
    read_only: bool | None = field(
        default=None,
    )
    write_only: bool | None = field(
        default=None,
    )
    examples: list[Any] | None = None
    discriminator: 'Discriminator | None' = None
    xml: 'XML | None' = None
    external_docs: 'ExternalDocumentation | None' = field(
        default=None,
    )
    example: Any | None = None


@dataclass(frozen=True, kw_only=True, slots=True)
class SchemaDataContainer(Schema):
    """TODO: add docs."""

    data_container: Any = None
