from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, final

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


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class Schema:
    """
    The Schema Object allows the definition of input and output data types.

    These types can be objects, but also primitives and arrays. Unless stated
    otherwise, the property definitions follow those of JSON Schema and
    do not add any additional semantics. Where JSON Schema indicates that
    behavior is defined by the application (e.g. for annotations),
    OAS also defers the definition of semantics to the application consuming
    the OpenAPI document.
    """

    all_of: 'Sequence[Reference | Schema] | None' = None
    any_of: 'Sequence[Reference | Schema] | None' = None
    one_of: 'Sequence[Reference | Schema] | None' = None
    schema_not: 'Reference | Schema | None' = None
    schema_if: 'Reference | Schema | None' = None
    then: 'Reference | Schema | None' = None
    schema_else: 'Reference | Schema | None' = None
    dependent_schemas: 'dict[str, Reference | Schema] | None' = None
    prefix_items: 'Sequence[Reference | Schema] | None' = None
    items: 'Reference | Schema | None' = None
    contains: 'Reference | Schema | None' = None
    properties: 'dict[str, Reference | Schema] | None' = None
    pattern_properties: 'dict[str, Reference | Schema] | None' = None
    additional_properties: 'Reference | Schema | bool | None' = None
    property_names: 'Reference | Schema | None' = None
    unevaluated_items: 'Reference | Schema | None' = None
    unevaluated_properties: 'Reference | Schema | None' = None
    type: 'OpenAPIType | Sequence[OpenAPIType] | None' = None
    enum: Sequence[Any] | None = None
    const: Any | None = None
    multiple_of: float | None = None
    maximum: float | None = None
    exclusive_maximum: float | None = None
    minimum: float | None = None
    exclusive_minimum: float | None = None
    max_length: int | None = None
    min_length: int | None = None
    pattern: str | None = None
    max_items: int | None = None
    min_items: int | None = None
    unique_items: bool | None = None
    max_contains: int | None = None
    min_contains: int | None = None
    max_properties: int | None = None
    min_properties: int | None = None
    required: Sequence[str] | None = None
    dependent_required: dict[str, Sequence[str]] | None = None
    format: 'OpenAPIFormat | None' = None
    content_encoding: str | None = None
    content_media_type: str | None = None
    content_schema: 'Reference | Schema | None' = None
    title: str | None = None
    description: str | None = None
    default: Any | None = None
    deprecated: bool | None = None
    read_only: bool | None = None
    write_only: bool | None = None
    examples: list[Any] | None = None
    discriminator: 'Discriminator | None' = None
    xml: 'XML | None' = None
    external_docs: 'ExternalDocumentation | None' = None
    example: Any | None = None
