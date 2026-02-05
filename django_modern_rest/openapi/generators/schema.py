import contextlib
import dataclasses
from collections import OrderedDict, defaultdict, deque
from collections.abc import (
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Sequence,
)
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
)
from pathlib import Path
from re import Pattern
from types import MappingProxyType, NoneType, UnionType
from typing import Annotated, Any, Final, Union, get_args, get_origin
from uuid import UUID

from django_modern_rest.openapi.core.registry import SchemaRegistry
from django_modern_rest.openapi.extractors.finder import find_extractor
from django_modern_rest.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.schema import Schema
from django_modern_rest.openapi.types import FieldDefinition, KwargDefinition

_SCHEMA_ARRAY: Final = Schema(type=OpenAPIType.ARRAY)

# TODO: Possible place for refactoring.
_TYPE_MAP: Final = MappingProxyType({
    Decimal: Schema(type=OpenAPIType.NUMBER),
    defaultdict: Schema(type=OpenAPIType.OBJECT),
    deque: _SCHEMA_ARRAY,
    dict: Schema(type=OpenAPIType.OBJECT),
    frozenset: _SCHEMA_ARRAY,
    IPv4Address: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv4Interface: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv4Network: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV4),
    IPv6Address: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    IPv6Interface: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    IPv6Network: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.IPV6),
    Iterable: _SCHEMA_ARRAY,  # pyright: ignore[reportArgumentType]
    list: _SCHEMA_ARRAY,
    Mapping: Schema(type=OpenAPIType.OBJECT),
    MutableMapping: Schema(type=OpenAPIType.OBJECT),
    MutableSequence: _SCHEMA_ARRAY,
    None: Schema(type=OpenAPIType.NULL),
    NoneType: Schema(type=OpenAPIType.NULL),
    OrderedDict: Schema(type=OpenAPIType.OBJECT),
    Path: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI),
    Pattern: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.REGEX),
    Sequence: _SCHEMA_ARRAY,
    set: _SCHEMA_ARRAY,
    tuple: _SCHEMA_ARRAY,
    UUID: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.UUID),
    bool: Schema(type=OpenAPIType.BOOLEAN),
    bytearray: Schema(type=OpenAPIType.STRING),
    bytes: Schema(type=OpenAPIType.STRING),
    date: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE),
    datetime: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE_TIME),
    float: Schema(type=OpenAPIType.NUMBER),
    int: Schema(type=OpenAPIType.INTEGER),
    str: Schema(type=OpenAPIType.STRING),
    time: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DURATION),
    timedelta: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DURATION),
})

# TODO: We need to move this to the FieldExtractor
# (and maybe replace the dictionary with something else)
# for the possibility of redefinition in plugins.
_KWARG_TO_SCHEMA_MAP: Final = MappingProxyType({
    'content_encoding': 'content_encoding',
    'default': 'default',
    'title': 'title',
    'description': 'description',
    'const': 'const',
    'gt': 'exclusive_minimum',
    'ge': 'minimum',
    'lt': 'exclusive_maximum',
    'le': 'maximum',
    'multiple_of': 'multiple_of',
    'min_items': 'min_items',
    'max_items': 'max_items',
    'min_length': 'min_length',
    'max_length': 'max_length',
    'pattern': 'pattern',
    'format': 'format',
    'enum': 'enum',
    'read_only': 'read_only',
    'examples': 'examples',
    'external_docs': 'external_docs',
})


class SchemaGenerator:
    """Generate FieldDefinition from dtos."""

    def __init__(self, registry: SchemaRegistry) -> None:
        """Init empty registry."""
        self.registry = registry

    def generate(self, annotation: Any) -> Schema | Reference:
        """Get schema for a type."""
        simple_schema = _get_schema_from_type_map(
            annotation,
        ) or self.registry.get_reference(annotation)
        if simple_schema:
            return simple_schema

        origin = get_origin(annotation) or annotation

        if origin is Annotated:
            return self.generate(get_args(annotation)[0])

        generic_schema = _handle_generic_types(
            self,
            origin,
            get_args(annotation),
        )
        if generic_schema:
            return generic_schema

        return self._generate_reference(annotation)

    def _generate_reference(self, source_type: Any) -> Reference:
        field_definitions = find_extractor(
            source_type,
        ).extract_fields(source_type)
        props, required = self._extract_properties(field_definitions)

        return self.registry.register(
            source_type=source_type,
            schema=Schema(
                type=OpenAPIType.OBJECT,
                properties=props,
                required=required or None,
            ),
            name=source_type.__name__,
        )

    def _extract_properties(
        self,
        field_definitions: list[FieldDefinition],
    ) -> tuple[dict[str, Schema | Reference], list[str]]:
        props: dict[str, Schema | Reference] = {}
        required: list[str] = []

        for field_definition in field_definitions:
            schema = self.generate(
                field_definition.annotation,
            )

            if field_definition.kwarg_definition:
                schema = self._apply_kwarg_definition(
                    schema,
                    field_definition.kwarg_definition,
                )

            props[field_definition.name] = schema

            if field_definition.extra_data.get('is_required'):
                required.append(field_definition.name)
        return props, required

    def _apply_kwarg_definition(
        self,
        schema: Schema | Reference,
        kwarg_definition: KwargDefinition,
    ) -> Schema | Reference:
        if isinstance(schema, Reference):
            # TODO: handle Reference wrapping with allOf?
            return schema

        updates = self._get_kwarg_update(schema, kwarg_definition)

        if not updates:
            return schema

        return dataclasses.replace(schema, **updates)

    def _get_kwarg_update(
        self,
        schema: Schema,
        kwarg_definition: KwargDefinition,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        for kwarg_field, schema_field in _KWARG_TO_SCHEMA_MAP.items():
            kwarg_value = getattr(kwarg_definition, kwarg_field)
            if kwarg_value is None:
                continue

            if kwarg_field == 'format':
                with contextlib.suppress(ValueError):
                    kwarg_value = OpenAPIFormat(kwarg_value)

            updates[schema_field] = kwarg_value
        return updates


def _get_schema_from_type_map(annotation: Any) -> Schema | None:
    type_schema = _TYPE_MAP.get(annotation)
    if type_schema:
        return type_schema

    if isinstance(annotation, type):
        for base in annotation.mro():
            base_schema = _TYPE_MAP.get(base)
            if base_schema:
                return base_schema
    return None


def _handle_generic_types(
    generator: SchemaGenerator,
    origin: Any,
    args: tuple[Any, ...],
) -> Schema | Reference | None:
    if origin is UnionType or origin is Union:
        return _handle_union(generator, args)

    if isinstance(origin, type) and issubclass(origin, Mapping):
        return _handle_mapping(generator, args)

    if (
        isinstance(origin, type)
        and issubclass(origin, Sequence)
        and origin not in {str, bytes, bytearray}
    ):
        return _handle_sequence(generator, args)

    return None


def _handle_union(
    generator: SchemaGenerator,
    args: tuple[Any, ...],
) -> Schema | Reference:
    real_args = [arg for arg in args if arg not in {NoneType, type(None)}]
    if not real_args:
        return _TYPE_MAP[NoneType]

    if len(real_args) == 1:
        return generator.generate(real_args[0])

    return Schema(
        one_of=[generator.generate(arg) for arg in real_args],
    )


def _handle_mapping(
    generator: SchemaGenerator,
    args: tuple[Any, ...],
) -> Schema:
    value_type = args[1] if len(args) >= 2 else Any
    return Schema(
        type=OpenAPIType.OBJECT,
        additional_properties=generator.generate(value_type),
    )


def _handle_sequence(
    generator: SchemaGenerator,
    args: tuple[Any, ...],
) -> Schema:
    items_schema = None
    if args:
        items_schema = generator.generate(args[0])
    return Schema(type=OpenAPIType.ARRAY, items=items_schema)
