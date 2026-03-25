# NOTE: when editing this file, also edit `test_pydantic_schema.py`

import enum
from collections.abc import Collection, Mapping
from typing import Annotated, Any, Final, Literal, Optional, Union

import pytest
from typing_extensions import TypedDict

from dmr.exceptions import UnsolvableAnnotationsError
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.schema import SchemaGenerator
from dmr.openapi.objects import OpenAPIType, Reference, Schema

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)


@pytest.fixture
def schema_generator(openapi_context: OpenAPIContext) -> SchemaGenerator:
    """Fixture for ``SchemaGenerator`` class."""
    return openapi_context.generators.schema


class _TestClass:
    attr: int


class _TestTypedDict(TypedDict):
    attr: int


class _TestEnum(enum.IntEnum):
    height = 1
    width = 2


_TEST_SCHEMA: Final = Schema(type=OpenAPIType.OBJECT)


@pytest.mark.parametrize(
    ('source_type', 'schema_type'),
    [
        (int, OpenAPIType.INTEGER),
        (float, OpenAPIType.NUMBER),
        (str, OpenAPIType.STRING),
        (bytes, OpenAPIType.STRING),
        (bool, OpenAPIType.BOOLEAN),
        (None, OpenAPIType.NULL),
    ],
)
def test_simple_types(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    schema_type: OpenAPIType,
) -> None:
    """Ensure schema is generated correctly for simple types."""
    schema = schema_generator(source_type, MsgspecSerializer)

    assert isinstance(schema, Schema)
    assert schema.type == schema_type, source_type


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            list[int],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.INTEGER),
            ),
        ),
        (
            list,
            Schema(type=OpenAPIType.ARRAY),
        ),
        (
            set[float],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.NUMBER),
            ),
        ),
        (
            frozenset[str],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.STRING),
            ),
        ),
        # `Iterable[T]` is not supported by `msgspec`
        (
            Collection[str],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.STRING),
            ),
        ),
        (
            tuple[bool, ...],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.BOOLEAN),
            ),
        ),
        (
            tuple[int, str],
            Schema(
                type=OpenAPIType.ARRAY,
                items=False,
                max_items=2,
                min_items=2,
                prefix_items=[
                    Schema(type=OpenAPIType.INTEGER),
                    Schema(type=OpenAPIType.STRING),
                ],
            ),
        ),
        (
            tuple[()],
            Schema(
                type=OpenAPIType.ARRAY,
                items=None,
                max_items=0,
                min_items=0,
            ),
        ),
        (
            dict[str, int],
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.INTEGER),
            ),
        ),
        (
            dict[str, Any],
            Schema(type=OpenAPIType.OBJECT),
        ),
        (
            dict,
            Schema(type=OpenAPIType.OBJECT),
        ),
        (
            Mapping[str, float],
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.NUMBER),
            ),
        ),
    ],
)
def test_generic_objects(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for generic objects."""
    schema = schema_generator(source_type, MsgspecSerializer)

    assert isinstance(schema, Schema)
    assert schema == expected_schema, source_type


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            Optional[None],  # noqa: UP045
            Schema(type=OpenAPIType.NULL),
        ),
        (
            Optional[int],  # noqa: UP045
            Schema(
                any_of=[
                    Schema(type=OpenAPIType.INTEGER),
                    Schema(type=OpenAPIType.NULL),
                ],
            ),
        ),
        (
            Union[None, None],  # noqa: UP007
            Schema(type=OpenAPIType.NULL),
        ),
        (
            Union[str, int, None],  # noqa: UP007
            Schema(
                any_of=[
                    Schema(type=OpenAPIType.STRING),
                    Schema(type=OpenAPIType.INTEGER),
                    Schema(type=OpenAPIType.NULL),
                ],
            ),
        ),
        (
            bool | float,
            Schema(
                any_of=[
                    Schema(type=OpenAPIType.BOOLEAN),
                    Schema(type=OpenAPIType.NUMBER),
                ],
            ),
        ),
    ],
)
def test_union_schema(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for generic objects."""
    schema = schema_generator(source_type, MsgspecSerializer)

    assert isinstance(schema, Schema)
    assert schema == expected_schema, source_type


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            Annotated[dict[str, int], 'meta'],
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.INTEGER),
            ),
        ),
        (
            Annotated[str, 'meta'],
            Schema(type=OpenAPIType.STRING),
        ),
        (
            Annotated[str | int, 'meta'],
            Schema(
                any_of=[
                    Schema(type=OpenAPIType.STRING),
                    Schema(type=OpenAPIType.INTEGER),
                ],
            ),
        ),
    ],
)
def test_annotated_objects(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for annotated."""
    schema = schema_generator(source_type, MsgspecSerializer)

    assert isinstance(schema, Schema)
    assert schema == expected_schema, source_type


def test_enum(
    schema_generator: SchemaGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure schema for enums is correct."""
    reference = schema_generator(_TestEnum, MsgspecSerializer)
    assert isinstance(reference, Reference)

    schema = openapi_context.registries.schema.maybe_resolve_reference(
        reference,
    )
    assert schema == Schema(enum=[1, 2], title=_TestEnum.__qualname__)


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            Literal[1, 2],
            Schema(enum=[1, 2]),
        ),
        # `Literal[]` with different types is not supported by `msgspec`
    ],
)
def test_literal_types(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for literal types."""
    schema = schema_generator(source_type, MsgspecSerializer)

    assert isinstance(schema, Schema)
    assert schema == expected_schema, source_type


def test_type_mapper_typeddict(
    schema_generator: SchemaGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that schema for ``TypedDict`` returns ``None``."""
    reference = schema_generator(_TestTypedDict, MsgspecSerializer)
    assert isinstance(reference, Reference)

    schema = openapi_context.registries.schema.maybe_resolve_reference(
        reference,
    )
    assert schema == Schema(
        type=OpenAPIType.OBJECT,
        title=_TestTypedDict.__qualname__,
        required=['attr'],
        properties={'attr': Schema(type=OpenAPIType.INTEGER)},
    )


def test_unsupported_type(schema_generator: SchemaGenerator) -> None:
    """Ensures that unsupported types raise."""
    with pytest.raises(
        UnsolvableAnnotationsError,
        match='Cannot generate OpenAPI schema',
    ):
        schema_generator(_TestClass, MsgspecSerializer)
