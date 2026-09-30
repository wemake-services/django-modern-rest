# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false

from enum import Enum
from typing import Any, TypeVar

from dmr.internal.types import EMPTY
from dmr.openapi.objects import (
    XML,
    Discriminator,
    ExternalDocumentation,
    OpenAPIFormat,
    OpenAPIType,
    Schema,
)

_EnumT = TypeVar('_EnumT', bound=Enum)


def load_schema(raw_data: dict[str, Any]) -> Schema:
    """
    Load schema from Python's dict into a dataclass.

    Sadly, we can't use ``serializer.from_python`` until
    this problem with ``msgspec`` is fixed:
    https://github.com/msgspec/msgspec/issues/982

    After that we will just use the serializer and remove this code.

    .. versionchanged:: 0.16.0
        Does not generate examples anymore, because which keyword
        they land on depends on the target OpenAPI version.
        :func:`dmr.openapi.mappers.example.set_generated_example`
        does that now.
        Subschemas with ``$ref`` are loaded as :class:`Schema` objects
        with :attr:`Schema.ref` set, keeping their sibling keywords,
        as OpenAPI 3.1 requires. They are not
        :class:`~dmr.openapi.objects.Reference` objects anymore.
        Specification extensions, like ``x-thing``,
        are now kept in :attr:`Schema.extensions`, #1491

    """
    return Schema(
        all_of=_try_sequence(raw_data.get('allOf')),
        any_of=_sort_null_last(_try_sequence(raw_data.get('anyOf'))),
        one_of=_sort_null_last(_try_sequence(raw_data.get('oneOf'))),
        schema_not=_try_optional_type(raw_data.get('not')),
        schema_if=_try_optional_type(raw_data.get('if')),
        schema_then=_try_optional_type(raw_data.get('then')),
        schema_else=_try_optional_type(raw_data.get('else')),
        dependent_schemas=_try_dict(raw_data.get('dependentSchemas')),
        prefix_items=_try_sequence(raw_data.get('prefixItems')),
        items=_try_optional_bool_type(raw_data.get('items')),
        contains=_try_optional_type(raw_data.get('contains')),
        properties=_try_dict(raw_data.get('properties')),
        pattern_properties=_try_dict(raw_data.get('patternProperties')),
        additional_properties=_try_optional_bool_type(
            raw_data.get('additionalProperties'),
        ),
        property_names=_try_optional_type(raw_data.get('propertyNames')),
        unevaluated_items=_try_optional_type(raw_data.get('unevaluatedItems')),
        unevaluated_properties=_try_optional_type(
            raw_data.get('unevaluatedProperties'),
        ),
        type=_try_type_field(raw_data.get('type')),
        enum=raw_data.get('enum'),
        const=raw_data.get('const', EMPTY),
        multiple_of=raw_data.get('multipleOf'),
        maximum=raw_data.get('maximum'),
        exclusive_maximum=raw_data.get('exclusiveMaximum'),
        minimum=raw_data.get('minimum'),
        exclusive_minimum=raw_data.get('exclusiveMinimum'),
        max_length=raw_data.get('maxLength'),
        min_length=raw_data.get('minLength'),
        pattern=raw_data.get('pattern'),
        max_items=raw_data.get('maxItems'),
        min_items=raw_data.get('minItems'),
        unique_items=raw_data.get('uniqueItems'),
        max_contains=raw_data.get('maxContains'),
        min_contains=raw_data.get('minContains'),
        max_properties=raw_data.get('maxProperties'),
        min_properties=raw_data.get('minProperties'),
        required=raw_data.get('required', []),
        dependent_required=raw_data.get('dependentRequired'),
        format=_try_format(raw_data.get('format')),
        content_encoding=raw_data.get('contentEncoding'),
        content_media_type=raw_data.get('contentMediaType'),
        content_schema=_try_optional_type(raw_data.get('contentSchema')),
        title=raw_data.get('title'),
        description=raw_data.get('description'),
        default=raw_data.get('default', EMPTY),
        deprecated=raw_data.get('deprecated'),
        read_only=raw_data.get('readOnly'),
        write_only=raw_data.get('writeOnly'),
        discriminator=_try_discriminator(raw_data.get('discriminator')),
        xml=_try_xml(raw_data.get('xml')),
        external_docs=_try_external_documentation(raw_data.get('externalDocs')),
        examples=raw_data.get('examples'),
        example=raw_data.get('example', EMPTY),
        dynamic_ref=raw_data.get('$dynamicRef'),
        dynamic_anchor=raw_data.get('$dynamicAnchor'),
        ref=raw_data.get('$ref'),
        anchor=raw_data.get('$anchor'),
        comment=raw_data.get('$comment'),
        schema_uri=raw_data.get('$schema'),
        defs=_try_dict(raw_data.get('$defs')),
        extensions=_try_extensions(raw_data),
    )


def _try_optional_bool_type(raw_value: Any) -> Schema | bool | None:
    """Load a raw_value as Schema, or bool, or None."""
    return (
        raw_value
        if isinstance(raw_value, bool)
        else _try_optional_type(raw_value)
    )


def _try_optional_type(raw_value: Any) -> Schema | None:
    """Load a raw_value as Schema, or None."""
    return None if raw_value is None else load_schema(raw_value)  # noqa: WPS204


def _try_extensions(raw_data: dict[str, Any]) -> dict[str, Any] | None:
    """Keep specification extensions, like ``x-thing``, as they are."""
    extensions = {
        raw_key: raw_value
        for raw_key, raw_value in raw_data.items()
        if raw_key.startswith('x-')
    }
    return extensions or None


def _try_sequence(raw_value: Any) -> list[Schema] | None:
    """Load a list of Schema values, or None."""
    return (
        None
        if raw_value is None
        else [load_schema(seq_item) for seq_item in raw_value]
    )


def _try_dict(raw_value: Any) -> dict[str, Schema] | None:
    """Load a dict of str -> Schema values, or None."""
    return (
        None
        if raw_value is None
        else {
            dict_key: load_schema(dict_value)
            for dict_key, dict_value in raw_value.items()
        }
    )


def _try_type_field(raw_value: Any) -> OpenAPIType | list[OpenAPIType] | None:
    """Load 'type' which can be a single string or a list of strings."""
    if isinstance(raw_value, list):
        return [OpenAPIType(seq_value) for seq_value in raw_value]
    return None if raw_value is None else OpenAPIType(raw_value)


def _try_format(raw_value: Any) -> OpenAPIFormat | str | None:
    """Load a known format as an enum member or arbitrary string."""
    if raw_value is None:
        return None
    try:
        return OpenAPIFormat(raw_value)
    except ValueError:
        return str(raw_value)


def _try_discriminator(raw_value: Any) -> Discriminator | None:
    return (
        None
        if raw_value is None
        else Discriminator(
            property_name=raw_value['propertyName'],
            mapping=raw_value.get('mapping'),
            default_mapping=raw_value.get('defaultMapping'),
        )
    )


def _try_external_documentation(raw_value: Any) -> ExternalDocumentation | None:
    return (
        None
        if raw_value is None
        else ExternalDocumentation(
            url=raw_value['url'],
            description=raw_value.get('description'),
        )
    )


def _try_xml(raw_value: Any) -> XML | None:
    return (
        None
        if raw_value is None
        else XML(
            name=raw_value.get('name'),
            namespace=raw_value.get('namespace'),
            prefix=raw_value.get('prefix'),
            attribute=raw_value.get('attribute'),
            wrapped=raw_value.get('wrapped'),
            node_type=raw_value.get('nodeType'),
        )
    )


def _sort_null_last(
    sequence: list[Schema] | None,
) -> list[Schema] | None:
    # See https://github.com/wemake-services/django-modern-rest/issues/990
    # TODO: remove once solved: https://github.com/msgspec/msgspec/issues/1027
    return (
        None
        if sequence is None
        else (
            [schema for schema in sequence if schema.type != OpenAPIType.NULL]
            + [schema for schema in sequence if schema.type == OpenAPIType.NULL]
        )
    )
