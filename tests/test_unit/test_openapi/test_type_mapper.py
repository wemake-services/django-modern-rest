from decimal import Decimal
from typing import Any, Final, TypedDict

import pytest

from django_modern_rest.openapi.objects.enums import OpenAPIType
from django_modern_rest.openapi.objects.schema import Schema
from django_modern_rest.openapi.type_mapping import TypeMapper


@pytest.fixture
def type_mapper() -> type[TypeMapper]:
    """Fixtutre for ``TypeMapper`` class."""
    return TypeMapper


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
        (bool, OpenAPIType.BOOLEAN),
        (_SubDecimal, OpenAPIType.NUMBER),
    ],
)
def test_type_mapper_get_schema(
    source_type: Any,
    schema_type: OpenAPIType,
    *,
    type_mapper: TypeMapper,
) -> None:
    """Ensure ``TypeMapper.get_schema`` works."""
    schema = type_mapper.get_schema(source_type)

    assert schema is not None
    assert schema.type == schema_type


def test_type_mapper_register_works(type_mapper: TypeMapper) -> None:
    """Ensure ``TypeMapper`` register new ``Schema``."""
    type_mapper.register(_TestClass, _TEST_SCHEMA)

    schema = type_mapper.get_schema(_TestClass)
    assert schema == _TEST_SCHEMA


def test_type_mapper_register_raise_error(type_mapper: TypeMapper) -> None:
    """Ensure ``TypeMapper`` raise error if register available ``Schema``."""
    with pytest.raises(ValueError, match='already registered'):
        type_mapper.register(int, _TEST_SCHEMA)


def test_type_mapper_override(type_mapper: TypeMapper) -> None:
    """Ensure ``TypeMapper.override`` works."""
    type_mapper.override(int, _TEST_SCHEMA)

    int_schema = type_mapper.get_schema(int)
    assert int_schema == _TEST_SCHEMA


def test_type_mapper_typeddict(type_mapper: TypeMapper) -> None:
    """Ensure ``TypeMapper`` returns ``None`` for ``TypedDict``."""
    schema = type_mapper.get_schema(_TestTypedDict)
    assert schema is None
