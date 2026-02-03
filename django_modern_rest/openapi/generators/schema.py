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
from typing import Any, Final, Union, get_args, get_origin
from uuid import UUID

from django_modern_rest.openapi.core.registry import SchemaRegistry
from django_modern_rest.openapi.extractors.base import FieldExtractor
from django_modern_rest.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.schema import Schema

_SCHEMA_ARRAY: Final = Schema(type=OpenAPIType.ARRAY)

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


class SchemaGenerator:
    """Generate FieldDefinition from dtos."""

    def __init__(self) -> None:
        """Init empty registry."""
        self.registry = SchemaRegistry()

    def generate(self, source_type: Any) -> Reference:
        """Get or creage Reference for source_type."""
        existing_ref = self.registry.get_reference(source_type)
        if existing_ref:
            return existing_ref

        extractor = _find_extractor(source_type)

        field_definitions = extractor.extract_fields(source_type)

        props = {
            field_definition.name: self._get_schema_for_type(
                field_definition.annotation,
            )
            for field_definition in field_definitions
        }

        schema = Schema(
            type=OpenAPIType.OBJECT,
            properties=props,
        )
        return self.registry.register(
            source_type=source_type,
            schema=schema,
            name=source_type.__name__,
        )

    def _get_from_type_map(self, annotation: Any) -> Schema | None:
        type_schema = _TYPE_MAP.get(annotation)
        if type_schema:
            return type_schema

        if isinstance(annotation, type):
            for base in annotation.mro():
                base_schema = _TYPE_MAP.get(base)
                if base_schema:
                    return base_schema
        return None

    def _get_schema_for_type(self, annotation: Any) -> Schema | Reference:
        simple_schema = self._get_from_type_map(
            annotation,
        ) or self.registry.get_reference(annotation)
        if simple_schema:
            return simple_schema

        origin = get_origin(annotation) or annotation
        args = get_args(annotation)

        if origin is UnionType or origin is Union:
            return self._handle_union(args)

        if isinstance(origin, type) and issubclass(origin, Mapping):
            return self._handle_mapping(args)

        if (
            isinstance(origin, type)
            and issubclass(origin, Sequence)
            and origin not in {str, bytes, bytearray}
        ):
            return self._handle_sequence(args)

        return self.generate(annotation)

    def _handle_union(self, args: tuple[Any, ...]) -> Schema | Reference:
        real_args = [arg for arg in args if arg not in {NoneType, type(None)}]

        if not real_args:
            return _TYPE_MAP[NoneType]

        if len(real_args) == 1:
            return self._get_schema_for_type(real_args[0])

        return Schema(
            any_of=[self._get_schema_for_type(arg) for arg in real_args],
        )

    def _handle_mapping(self, args: tuple[Any, ...]) -> Schema:
        value_type = args[1] if len(args) >= 2 else Any
        return Schema(
            type=OpenAPIType.OBJECT,
            additional_properties=self._get_schema_for_type(value_type),
        )

    def _handle_sequence(self, args: tuple[Any, ...]) -> Schema:
        items_schema = None
        if args:
            items_schema = self._get_schema_for_type(args[0])
        return Schema(type=OpenAPIType.ARRAY, items=items_schema)


def _find_extractor(source_type: Any) -> FieldExtractor[Any]:
    for extractor in FieldExtractor.registry:
        if extractor.is_supported(source_type):
            return extractor()
    raise ValueError(f'Field extractor for {source_type} not found')
