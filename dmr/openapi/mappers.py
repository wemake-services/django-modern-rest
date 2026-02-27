import contextlib
from collections import OrderedDict, defaultdict, deque
from collections.abc import (
    Callable,
    Collection,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Sequence,
    Set,
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
from types import NoneType, UnionType
from typing import (  # noqa: WPS235
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Optional,
    TypeAlias,
    Union,
    get_args,
    get_origin,
)
from uuid import UUID

from typing_extensions import is_typeddict

from dmr.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema

if TYPE_CHECKING:
    from dmr.openapi.generators.schema import SchemaGenerator
    from dmr.openapi.types import KwargDefinition


SchemaPredicate: TypeAlias = Callable[[Any, Any, tuple[Any, ...]], bool]
SchemaCallback: TypeAlias = Callable[
    [Any, Any, tuple[Any, ...], 'SchemaGenerator'],
    Schema,
]
ReferencedSchemaCallback: TypeAlias = Callable[
    [Any, Any, tuple[Any, ...], 'SchemaGenerator'],
    Schema | Reference,
]
SchemaOrCallback: TypeAlias = Schema | SchemaCallback
_PredicatePair: TypeAlias = tuple[SchemaPredicate, ReferencedSchemaCallback]


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


def _generic_array(
    annotation: Any,
    origin: Any,
    type_args: tuple[Any, ...],
    generator: 'SchemaGenerator',
) -> Schema:
    items_schema = generator(type_args[0] if type_args else Any)
    return Schema(type=OpenAPIType.ARRAY, items=items_schema)


def _generic_object(
    annotation: Any,
    origin: Any,
    type_args: tuple[Any, ...],
    generator: 'SchemaGenerator',
) -> Schema:
    value_type = type_args[1] if len(type_args) >= 2 else Any
    return Schema(
        type=OpenAPIType.OBJECT,
        additional_properties=generator(value_type),
    )


def _handle_union(
    annotation: Any,
    origin: Any,
    type_args: tuple[Any, ...],
    generator: 'SchemaGenerator',
) -> Schema | Reference:
    if not type_args:
        # We know that NoneType is registered in TypeMapper
        schema = TypeMapper.get_schema(None, generator)
        # for mypy: we know that `None` is registered
        assert schema is not None  # noqa: S101
        return schema
    return Schema(one_of=[generator(type_arg) for type_arg in type_args])


def _handle_annotated(
    annotation: Any,
    origin: Any,
    type_args: tuple[Any, ...],
    generator: 'SchemaGenerator',
) -> Schema | Reference:
    if not type_args:
        raise ValueError(
            'Cannot generate schema from just `Annotated` type, '
            'at least one type argument and a metadata are required: '
            '`Annotated[YourType, metadata]`',
        )
    # TODO: support metadata from `Annotated` to pass to schema's kwargs?
    # Example: `Annotated[int, Schema(maximum=0)]`
    return generator(type_args[0])


class TypeMapper:
    """Class to map Python types to OpenAPI schemas."""

    # Private API:
    _mapping: ClassVar[dict[Any, SchemaOrCallback]] = {
        # Fallback, which means "any json object":
        Any: Schema(type=OpenAPIType.OBJECT),
        # Real types:
        Decimal: Schema(type=OpenAPIType.NUMBER),
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
        None: Schema(type=OpenAPIType.NULL),
        NoneType: Schema(type=OpenAPIType.NULL),
        Path: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.URI),
        Pattern: Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.REGEX),
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
        # Arrays:
        Sequence: _generic_array,
        set: _generic_array,
        tuple: _generic_array,
        Iterable: _generic_array,
        list: _generic_array,
        frozenset: _generic_array,
        MutableSequence: _generic_array,
        deque: _generic_array,
        Set: _generic_array,
        Collection: _generic_array,
        # Objects:
        Mapping: _generic_object,
        OrderedDict: _generic_object,
        MutableMapping: _generic_object,
        defaultdict: _generic_object,
        dict: _generic_object,
    }

    _predicates: ClassVar[list[_PredicatePair]] = [
        # `Union[T, V]`, `Optional[T]`, or `T | V`:
        (
            lambda annotation, origin, type_args: (
                origin is Union or origin is UnionType or origin is Optional
            ),
            _handle_union,
        ),
        # `Annotated[T, metadata]`:
        (
            lambda annotation, origin, type_args: origin is Annotated,
            _handle_annotated,
        ),
    ]

    @classmethod
    def register(
        cls,
        source_type: Any,
        schema: SchemaOrCallback,
        *,
        override: bool = False,
    ) -> None:
        """Register a schema for a type."""
        if not override and source_type in cls._mapping:
            raise ValueError(
                f'Type {source_type!r} is already registered. '
                'Use override() to replace.',
            )
        cls._mapping[source_type] = schema

    @classmethod
    def get_schema(
        cls,
        annotation: Any,
        generator: 'SchemaGenerator',
    ) -> Schema | Reference | None:
        """Get schema for a type."""
        # Bail out on unsupported types:
        if is_typeddict(annotation):
            return None

        # We first try to find exact types:
        origin = get_origin(annotation) or annotation
        type_args = get_args(annotation)
        schema = cls._get_from_mapping(annotation, origin, type_args, generator)
        if schema:
            return schema

        # Next we try to find schema by predicate:
        for predicate, schema_generator in cls._predicates:
            if predicate(annotation, origin, type_args):
                return schema_generator(
                    annotation,
                    origin,
                    type_args,
                    generator,
                )

        # Next we try to find types by mro from existing exact types:
        return cls._traverse_mro(annotation, origin, type_args, generator)

    @classmethod
    def _get_from_mapping(
        cls,
        annotation: Any,
        origin: Any,
        type_args: tuple[Any, ...],
        generator: 'SchemaGenerator',
    ) -> Schema | None:
        schema = cls._mapping.get(origin)
        if callable(schema):
            return schema(annotation, origin, type_args, generator)
        if schema is not None:
            return schema
        return None

    @classmethod
    def _traverse_mro(
        cls,
        annotation: Any,
        origin: Any,
        type_args: tuple[Any, ...],
        generator: 'SchemaGenerator',
    ) -> Schema | None:
        for base in getattr(origin, '__mro__', ()):
            schema = cls._get_from_mapping(
                annotation,
                base,
                type_args,
                generator,
            )
            if schema:
                return schema

        # We did not find any:
        return None
