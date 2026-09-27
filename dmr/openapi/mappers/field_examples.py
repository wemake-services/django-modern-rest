# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

from collections.abc import Mapping
from typing import Any

from dmr.internal.types import EMPTY
from dmr.openapi.objects import OpenAPIType, Reference, Schema


def apply_field_examples(
    schema: Schema,
    example: Any,
    components: Mapping[str, Schema],
    schema_prefix: str,
) -> Any:
    """
    Puts hand-written field examples into a generated *example*.

    Generated examples of models have random values for all fields,
    even when a field has its own example. We take such examples
    from the JSON schema, so it works the same way for all serializers.

    Nested models are resolved from *components* by their references,
    *schema_prefix* is the prefix of these references.
    We only go into ``anyOf`` and ``oneOf`` for ``X | None``,
    for other unions we don't know which of the schemas was generated.

    .. versionadded:: 0.16.0
    """
    if example is EMPTY:
        return example  # examples are not generated

    optional_schema = _optional_schema(schema)
    if optional_schema is not None and example is not None:
        return _apply_field_example(
            optional_schema,
            example,
            components,
            schema_prefix,
        )
    if isinstance(example, dict) and schema.properties:
        return {
            field_name: _apply_field_example(
                schema.properties.get(field_name),
                field_value,
                components,
                schema_prefix,
            )
            for field_name, field_value in example.items()
        }
    if isinstance(example, list) and isinstance(
        schema.items,
        Schema | Reference,
    ):
        return [
            _apply_field_example(
                schema.items,
                item_value,
                components,
                schema_prefix,
            )
            for item_value in example
        ]
    return example


def _apply_field_example(
    field_schema: Reference | Schema | None,
    field_value: Any,
    components: Mapping[str, Schema],
    schema_prefix: str,
) -> Any:
    if isinstance(field_schema, Reference):
        field_schema = components.get(
            field_schema.ref.removeprefix(schema_prefix),
        )
        if field_schema is None:
            return field_value
    elif field_schema is None:
        return field_value
    elif field_schema.examples:
        return field_schema.examples[0]
    elif field_schema.example is not EMPTY:
        return field_schema.example
    return apply_field_examples(
        field_schema,
        field_value,
        components,
        schema_prefix,
    )


def _optional_schema(schema: Schema) -> Reference | Schema | None:
    """Returns ``X`` for ``X | None``, returns ``None`` for other schemas."""
    variants = [
        variant
        for variant in (schema.any_of or schema.one_of or [])
        if not isinstance(variant, Schema) or variant.type != OpenAPIType.NULL
    ]
    return variants[0] if len(variants) == 1 else None
