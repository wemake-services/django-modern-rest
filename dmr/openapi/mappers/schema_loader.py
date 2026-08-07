# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false

from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, TypeVar, overload

from typing_extensions import Sentinel

from dmr.openapi.mappers.example import generate_example
from dmr.openapi.objects import (
    XML,
    Discriminator,
    ExternalDocumentation,
    OpenAPIFormat,
    OpenAPIType,
    Reference,
    Schema,
)
from dmr.types import EMPTY

if TYPE_CHECKING:
    from dmr.serializer import BaseSerializer

_EnumT = TypeVar('_EnumT', bound=Enum)


# TODO: replace with Settings.schema_loader()
@overload
def load_schema(
    raw_data: dict[str, Any],
    *,
    should_generate_example: Literal[False] = False,
) -> Schema: ...


@overload
def load_schema(
    raw_data: dict[str, Any],
    *,
    should_generate_example: Literal[True],
    annotation: Any,
    serializer: type['BaseSerializer'],
) -> Schema: ...


def load_schema(
    raw_data: dict[str, Any],
    *,
    should_generate_example: bool = False,
    annotation: Any | Sentinel = EMPTY,
    serializer: type['BaseSerializer'] | None = None,
) -> Schema:
    """
    Load schema from Python's dict into a dataclass.

    Sadly, we can't use ``serializer.from_python`` until
    this problem with ``msgspec`` is fixed:
    https://github.com/msgspec/msgspec/issues/982

    After that we will just use the serializer and remove this code.
    """
    examples = raw_data.get('examples')
    example = raw_data.get('example')

    if should_generate_example and not example and not examples:
        assert serializer is not None, 'serializer instance is required'  # noqa: S101
        example = generate_example(annotation, serializer)

    raw_data['example'] = example
    return serializer.from_python(raw_data, Schema, strict=False)


def _try_optional_bool_type(raw_value: Any) -> Reference | Schema | bool | None:
    """Load a raw_value as Reference, or Schema, or bool, or None."""
    return (
        raw_value
        if isinstance(raw_value, bool)
        else _try_optional_type(raw_value)
    )


def _try_optional_type(raw_value: Any) -> Reference | Schema | None:
    """Load a raw_value as Reference (if it has '$ref') or Schema, or None."""
    return None if raw_value is None else _try_type(raw_value)  # noqa: WPS204


def _try_type(raw_value: Any) -> Reference | Schema:
    """Load a raw_value as Reference (if it has '$ref') or Schema."""
    if isinstance(raw_value, dict) and '$ref' in raw_value:
        return Reference(
            ref=raw_value['$ref'],
            summary=raw_value.get('summary'),
            description=raw_value.get('description'),
        )
    return load_schema(raw_value)


def _try_sequence(raw_value: Any) -> list[Reference | Schema] | None:
    """Load a list of Reference | Schema values, or None."""
    return (
        None
        if raw_value is None
        else [_try_type(seq_item) for seq_item in raw_value]
    )


def _try_dict(raw_value: Any) -> dict[str, Reference | Schema] | None:
    """Load a dict of str -> Reference | Schema values, or None."""
    return (
        None
        if raw_value is None
        else {
            dict_key: _try_type(dict_value)
            for dict_key, dict_value in raw_value.items()
        }
    )


def _try_additional_properties(
    raw_value: Any,
) -> Reference | Schema | bool | None:
    """Load additionalProperties which can also be a plain bool."""
    return (
        raw_value
        if isinstance(raw_value, bool)
        else _try_optional_type(raw_value)
    )


def _try_type_field(raw_value: Any) -> OpenAPIType | list[OpenAPIType] | None:
    """Load 'type' which can be a single string or a list of strings."""
    if isinstance(raw_value, list):  # pragma: no cover
        return [OpenAPIType(seq_value) for seq_value in raw_value]
    return None if raw_value is None else OpenAPIType(raw_value)


def _try_enum(enum_cls: type[_EnumT], raw_value: Any) -> _EnumT | None:
    """Load a raw_value as an enum member, or None."""
    return None if raw_value is None else enum_cls(raw_value)


def _try_discriminator(raw_value: Any) -> Discriminator | None:
    return (
        None
        if raw_value is None
        else Discriminator(
            property_name=raw_value['propertyName'],
            mapping=raw_value.get('mapping'),
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
            attribute=raw_value.get('attribute', False),
            wrapped=raw_value.get('wrapped', False),
        )
    )


def _sort_null_last(
    sequence: list[Reference | Schema] | None,
) -> list[Reference | Schema] | None:
    # See https://github.com/wemake-services/django-modern-rest/issues/990
    # TODO: remove once solved: https://github.com/msgspec/msgspec/issues/1027
    return (
        None
        if sequence is None
        else (
            [
                schema
                for schema in sequence
                if (
                    not isinstance(schema, Schema)
                    or schema.type != OpenAPIType.NULL
                )
            ]
            + [
                schema
                for schema in sequence
                if (
                    isinstance(schema, Schema)
                    and schema.type == OpenAPIType.NULL
                )
            ]
        )
    )
