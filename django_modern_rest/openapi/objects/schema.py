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
        metadata={'alias': 'allOf'},
    )
    any_of: 'Sequence[Reference | Schema] | None' = field(
        default=None,
        metadata={'alias': 'anyOf'},
    )
    schema_not: 'Reference | Schema | None' = field(
        default=None,
        metadata={'alias': 'not'},
    )
    schema_if: 'Reference | Schema | None' = field(
        default=None,
        metadata={'alias': 'if'},
    )
    then: 'Reference | Schema | None' = None
    schema_else: 'Reference | Schema | None' = field(
        default=None,
        metadata={'alias': 'else'},
    )
    dependent_schemas: 'dict[str, Reference | Schema] | None' = field(
        default=None,
        metadata={'alias': 'dependentSchemas'},
    )
    prefix_items: 'Sequence[Reference | Schema] | None' = field(
        default=None,
        metadata={'alias': 'prefixItems'},
    )
    items: 'Reference | Schema | None' = None
    contains: 'Reference | Schema | None' = None
    properties: 'dict[str, Reference | Schema] | None' = None
    pattern_properties: 'dict[str, Reference | Schema] | None' = field(
        default=None,
        metadata={'alias': 'patternProperties'},
    )
    additional_properties: 'Reference | Schema | bool | None' = field(
        default=None,
        metadata={'alias': 'additionalProperties'},
    )
    property_names: 'Reference | Schema | None' = field(
        default=None,
        metadata={'alias': 'propertyNames'},
    )
    unevaluated_items: 'Reference | Schema | None' = field(
        default=None,
        metadata={'alias': 'unevaluatedItems'},
    )
    unevaluated_properties: 'Reference | Schema | None' = field(
        default=None,
        metadata={'alias': 'unevaluatedProperties'},
    )
    type: 'OpenAPIType | Sequence[OpenAPIType] | None' = None
    enum: Sequence[Any] | None = None
    const: Any | None = None
    multiple_of: float | None = field(
        default=None,
        metadata={'alias': 'multipleOf'},
    )
    maximum: float | None = None
    exclusive_maximum: float | None = None
    minimum: float | None = None
    max_length: int | None = field(
        default=None,
        metadata={'alias': 'maxLength'},
    )
    min_length: int | None = field(
        default=None,
        metadata={'alias': 'minLength'},
    )
    pattern: str | None = None
    max_items: int | None = field(
        default=None,
        metadata={'alias': 'maxItems'},
    )
    min_items: int | None = field(default=None, metadata={'alias': 'minItems'})
    unique_items: bool | None = field(
        default=None,
        metadata={'alias': 'uniqueItems'},
    )
    max_contains: int | None = field(
        default=None,
        metadata={'alias': 'maxContains'},
    )
    min_contains: int | None = field(
        default=None,
        metadata={'alias': 'minContains'},
    )
    max_properties: int | None = field(
        default=None,
        metadata={'alias': 'maxProperties'},
    )
    min_properties: int | None = field(
        default=None,
        metadata={'alias': 'minProperties'},
    )
    required: Sequence[str] | None = None
    dependent_required: dict[str, Sequence[str]] | None = field(
        default=None,
        metadata={'alias': 'dependentRequired'},
    )
    format: 'OpenAPIFormat | None' = None
    content_encoding: str | None = field(
        default=None,
        metadata={'alias': 'contentEncoding'},
    )
    content_media_type: str | None = field(
        default=None,
        metadata={'alias': 'contentMediaType'},
    )
    content_schema: 'Reference | Schema | None' = field(
        default=None,
        metadata={'alias': 'contentSchema'},
    )
    title: str | None = None
    description: str | None = None
    default: Any | None = None
    deprecated: bool | None = None
    read_only: bool | None = field(
        default=None,
        metadata={'alias': 'readOnly'},
    )
    write_only: bool | None = field(
        default=None,
        metadata={'alias': 'writeOnly'},
    )
    examples: list[Any] | None = None
    discriminator: 'Discriminator | None' = None
    xml: 'XML | None' = None
    external_docs: 'ExternalDocumentation | None' = field(
        default=None,
        metadata={'alias': 'externalDocs'},
    )
    example: Any | None = None


@dataclass(frozen=True, kw_only=True, slots=True)
class SchemaDataContainer(Schema):
    """TODO: add docs."""

    data_container: Any = None
