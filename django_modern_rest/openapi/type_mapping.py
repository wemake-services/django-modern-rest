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
from types import NoneType
from typing import Any, ClassVar, Final
from uuid import UUID

from django_modern_rest.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from django_modern_rest.openapi.objects.schema import Schema

_SCHEMA_ARRAY: Final = Schema(type=OpenAPIType.ARRAY)


class TypeMapper:
    """Class to map Python types to OpenAPI schemas."""

    _type_map: ClassVar[dict[Any, Schema]] = {
        Decimal: Schema(type=OpenAPIType.NUMBER),
        defaultdict: Schema(type=OpenAPIType.OBJECT),
        deque: _SCHEMA_ARRAY,
        dict: Schema(type=OpenAPIType.OBJECT),
        frozenset: _SCHEMA_ARRAY,
        IPv4Address: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.IPV4,
        ),
        IPv4Interface: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.IPV4,
        ),
        IPv4Network: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.IPV4,
        ),
        IPv6Address: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.IPV6,
        ),
        IPv6Interface: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.IPV6,
        ),
        IPv6Network: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.IPV6,
        ),
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
        datetime: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.DATE_TIME,
        ),
        float: Schema(type=OpenAPIType.NUMBER),
        int: Schema(type=OpenAPIType.INTEGER),
        str: Schema(type=OpenAPIType.STRING),
        time: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DURATION),
        timedelta: Schema(
            type=OpenAPIType.STRING,
            format=OpenAPIFormat.DURATION,
        ),
    }

    @classmethod
    def get_schema(cls, annotation: Any) -> Schema | None:
        """Get schema for a type."""
        type_schema = cls._type_map.get(annotation)
        if type_schema:
            return type_schema

        if isinstance(annotation, type):
            for base in annotation.mro():
                base_schema = cls._type_map.get(base)
                if base_schema:
                    return base_schema
        return None

    @classmethod
    def register(cls, source_type: Any, schema: Schema) -> None:
        """Register a schema for a type."""
        if source_type in cls._type_map:
            raise ValueError(
                f'Type {source_type!r} is already registered. '
                'Use override() to replace.',
            )
        cls.override(source_type, schema)

    @classmethod
    def override(cls, source_type: Any, schema: Schema) -> None:
        """
        Register a schema for a type.

        Overwriting any existing registration.
        """
        cls._type_map[source_type] = schema
