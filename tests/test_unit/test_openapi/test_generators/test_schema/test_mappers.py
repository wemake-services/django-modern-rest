from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Annotated, Any, Final, Literal, Optional, Union

import pytest
from typing_extensions import TypedDict

from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.schema import SchemaGenerator
from dmr.openapi.objects.enums import OpenAPIType
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema


@pytest.fixture
def schema_generator(openapi_context: OpenAPIContext) -> SchemaGenerator:
    """Fixture for ``SchemaGenerator`` class."""
    return openapi_context.generators.schema


class _TestClass:
    attr: int


class _TestTypedDict(TypedDict):
    attr: int


class _SubDecimal(Decimal):
    """Test ``SubDecimal`` class."""


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
        (_SubDecimal, OpenAPIType.NUMBER),
    ],
)
def test_simple_types(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    schema_type: OpenAPIType,
) -> None:
    """Ensure schema is generated correctly for simple types."""
    schema = schema_generator(source_type)

    assert isinstance(schema, Schema)
    assert schema.type == schema_type


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
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.OBJECT),
            ),
        ),
        (
            set[float],
            Schema(
                type=OpenAPIType.ARRAY,
                items=Schema(type=OpenAPIType.NUMBER),
            ),
        ),
        (
            Iterable[str],
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
    ],
)
def test_generic_arrays(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for generic arrays."""
    schema = schema_generator(source_type)

    assert isinstance(schema, Schema)
    assert schema == expected_schema


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            dict[str, int],
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.INTEGER),
            ),
        ),
        (
            dict[str, Any],
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.OBJECT),
            ),
        ),
        (
            dict,
            Schema(
                type=OpenAPIType.OBJECT,
                additional_properties=Schema(type=OpenAPIType.OBJECT),
            ),
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
    schema = schema_generator(source_type)

    assert isinstance(schema, Schema)
    assert schema == expected_schema


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            Optional[None],  # noqa: UP045
            Schema(type=OpenAPIType.NULL),
        ),
        (
            Union[None, None],  # noqa: UP007
            Schema(type=OpenAPIType.NULL),
        ),
        (
            Union,
            Schema(type=OpenAPIType.NULL),
        ),
        (
            Optional,
            Schema(type=OpenAPIType.NULL),
        ),
        (
            Union[str, int, None],  # noqa: UP007
            Schema(
                one_of=[
                    Schema(type=OpenAPIType.STRING),
                    Schema(type=OpenAPIType.INTEGER),
                    Schema(type=OpenAPIType.NULL),
                ],
            ),
        ),
        (
            bool | float,
            Schema(
                one_of=[
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
    schema = schema_generator(source_type)

    assert isinstance(schema, Schema)
    assert schema == expected_schema


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
                one_of=[
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
    schema = schema_generator(source_type)

    assert isinstance(schema, Schema)
    assert schema == expected_schema


def test_annotated_error(schema_generator: SchemaGenerator) -> None:
    """Ensure schema is generated correctly for annotated."""
    with pytest.raises(ValueError, match=r'Annotated\[YourType'):
        schema_generator(Annotated)


@pytest.mark.parametrize(
    ('source_type', 'expected_schema'),
    [
        (
            Literal,
            Schema(type=OpenAPIType.OBJECT),
        ),
        (
            Literal[*()],
            Schema(type=OpenAPIType.OBJECT),
        ),
        (
            Literal[1, 2],
            Schema(enum=(1, 2)),
        ),
        (
            Literal[1, 'a', None, True],
            Schema(enum=(1, 'a', None, True)),
        ),
    ],
)
def test_literal_types(
    schema_generator: SchemaGenerator,
    *,
    source_type: Any,
    expected_schema: Schema,
) -> None:
    """Ensure schema is generated correctly for literal types."""
    schema = schema_generator(source_type)

    assert isinstance(schema, Schema)
    assert schema == expected_schema


def test_type_mapper_register_works(schema_generator: SchemaGenerator) -> None:
    """Ensure ``TypeMapper`` register new ``Schema``."""
    schema_generator.type_mapper.register(_TestClass, _TEST_SCHEMA)

    schema = schema_generator(_TestClass)

    assert schema == _TEST_SCHEMA


def test_type_mapper_register_raise_error(
    schema_generator: SchemaGenerator,
) -> None:
    """Ensure ``TypeMapper`` raise error if register available ``Schema``."""
    with pytest.raises(ValueError, match='already registered'):
        schema_generator.type_mapper.register(int, _TEST_SCHEMA)


def test_type_mapper_override(schema_generator: SchemaGenerator) -> None:
    """Ensure ``override=True`` works."""
    schema_generator.type_mapper.register(int, _TEST_SCHEMA, override=True)

    int_schema = schema_generator(int)

    assert int_schema == _TEST_SCHEMA


def test_type_mapper_typeddict(schema_generator: SchemaGenerator) -> None:
    """Ensure that schema for ``TypedDict`` returns ``None``."""
    schema = schema_generator(_TestTypedDict)

    assert isinstance(schema, Reference)
    assert schema.ref == f'#/components/schemas/{_TestTypedDict.__name__}'
