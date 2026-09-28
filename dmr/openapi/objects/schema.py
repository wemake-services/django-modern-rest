from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any

from dmr.internal.dataclass_aliases import Field
from dmr.internal.empty import EMPTY

if TYPE_CHECKING:
    from dmr.openapi.objects.discriminator import Discriminator
    from dmr.openapi.objects.enums import OpenAPIFormat, OpenAPIType
    from dmr.openapi.objects.external_documentation import ExternalDocumentation
    from dmr.openapi.objects.xml import XML


@dataclass(kw_only=True, slots=True)
class Schema:
    """
    The Schema Object allows the definition of input and output data types.

    These types can be objects, but also primitives and arrays. Unless stated
    otherwise, the property definitions follow those of JSON Schema and
    do not add any additional semantics. Where JSON Schema indicates that
    behavior is defined by the application (e.g. for annotations),
    OAS also defers the definition of semantics to the application consuming
    the OpenAPI document.

    .. versionchanged:: 0.16.0
        ``const``, ``default``, and ``example`` now default to
        :data:`~dmr.types.EMPTY` instead of ``None``,
        because ``None`` is a valid value for them.
        Subschemas are always ``Schema`` objects,
        since OpenAPI 3.1 a ``$ref`` inside a schema is a JSON Schema
        keyword (see ``ref``), not a :class:`Reference` object.

    """

    all_of: list['Schema'] | None = None
    any_of: list['Schema'] | None = None
    one_of: list['Schema'] | None = None
    schema_not: Annotated['Schema | None', Field(alias='not')] = None
    schema_if: Annotated['Schema | None', Field(alias='if')] = None
    schema_then: Annotated['Schema | None', Field(alias='then')] = None
    schema_else: Annotated['Schema | None', Field(alias='else')] = None
    dependent_schemas: dict[str, 'Schema'] | None = None
    prefix_items: list['Schema'] | None = None
    items: 'Schema | bool | None' = None
    contains: 'Schema | None' = None
    properties: dict[str, 'Schema'] | None = None
    pattern_properties: dict[str, 'Schema'] | None = None
    additional_properties: 'Schema | bool | None' = None
    property_names: 'Schema | None' = None
    unevaluated_items: 'Schema | None' = None
    unevaluated_properties: 'Schema | None' = None
    type: 'OpenAPIType | list[OpenAPIType] | None' = None
    enum: list[Any] | None = None
    const: Any = EMPTY
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
    required: list[str] = field(default_factory=list[str])
    dependent_required: dict[str, list[str]] | None = None
    format: 'OpenAPIFormat | str | None' = None
    content_encoding: str | None = None
    content_media_type: str | None = None
    content_schema: 'Schema | None' = None
    title: str | None = None
    description: str | None = None
    default: Any = EMPTY
    deprecated: bool | None = None
    read_only: bool | None = None
    write_only: bool | None = None
    examples: list[Any] | None = None
    discriminator: 'Discriminator | None' = None
    xml: 'XML | None' = None
    external_docs: 'ExternalDocumentation | None' = None
    example: Any = EMPTY
    dynamic_anchor: Annotated[str | None, Field(alias='$dynamicAnchor')] = None
    dynamic_ref: Annotated[str | None, Field(alias='$dynamicRef')] = None
    ref: Annotated[str | None, Field(alias='$ref')] = None
    anchor: Annotated[str | None, Field(alias='$anchor')] = None
    comment: Annotated[str | None, Field(alias='$comment')] = None
    schema_uri: Annotated[str | None, Field(alias='$schema')] = None
    defs: Annotated[
        dict[str, 'Schema'] | None,
        Field(alias='$defs'),
    ] = None
    extensions: dict[str, Any] | None = None
