import contextlib
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
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
)
from uuid import UUID

from typing_extensions import is_typeddict

from dmr.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from dmr.openapi.objects.schema import Schema

if TYPE_CHECKING:
    from dmr.openapi.types import KwargDefinition


_SCHEMA_ARRAY: Final = Schema(type=OpenAPIType.ARRAY)


class KwargMapper:
    """
    Class for mapping ``KwargDefinition`` to OpenAPI ``Schema``.

    This class is responsible for converting model-specific constraints
    into OpenAPI-compliant schema attributes.
    """

    __slots__ = ()

    # Public API:
    mapping: ClassVar[Mapping[str, str]] = {
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
    }

    def __call__(
        self,
        schema: 'Schema',
        kwarg_definition: 'KwargDefinition',
    ) -> dict[str, Any]:
        """
        Extract updates for the schema from the kwarg definition.

        Args:
            schema: The schema object to be updated.
            kwarg_definition: Data container with constraints.

        """
        updates: dict[str, Any] = {}
        for kwarg_field, schema_field in self.mapping.items():
            kwarg_value = getattr(kwarg_definition, kwarg_field)
            if kwarg_value is None:
                continue

            if kwarg_field == 'format':
                with contextlib.suppress(ValueError):
                    kwarg_value = OpenAPIFormat(kwarg_value)

            updates[schema_field] = kwarg_value

        if kwarg_definition.schema_extra:
            updates.update(kwarg_definition.schema_extra)

        return updates


class TypeMapper:
    """Class to map Python types to OpenAPI schemas."""

    # Private API:
    _mapping: ClassVar[dict[Any, Schema]] = {
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
        if is_typeddict(annotation):
            return None

        type_schema = cls._mapping.get(annotation)
        if type_schema:
            return type_schema

        if isinstance(annotation, type):
            for base in annotation.mro():
                base_schema = cls._mapping.get(base)
                if base_schema:
                    return base_schema
        return None

    @classmethod
    def register(cls, source_type: Any, schema: Schema) -> None:
        """Register a schema for a type."""
        if source_type in cls._mapping:
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
        cls._mapping[source_type] = schema
