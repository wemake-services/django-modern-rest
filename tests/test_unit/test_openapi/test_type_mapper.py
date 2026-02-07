from decimal import Decimal
from typing import Any, Final, TypedDict

import pytest

from django_modern_rest.openapi.objects.enums import OpenAPIType
from django_modern_rest.openapi.objects.schema import Schema
from django_modern_rest.openapi.type_mapping import TypeMapper


class _TestClass:
    attr: int


class _TestTypedDict(TypedDict):
    attr: int


class _SubDecimal(Decimal):
    """Test SubDecimal class."""


_TEST_SCHEMA: Final = Schema(type=OpenAPIType.OBJECT)


@pytest.mark.parametrize(
    ('source_type', 'schema_type'),
    [
        (int, OpenAPIType.INTEGER),
        (_SubDecimal, OpenAPIType.NUMBER),
    ],
)
def test_type_mapper_get_schema(
    source_type: Any,
    schema_type: OpenAPIType,
) -> None:
    """Ensure TypeMapper get_type works."""
    schema = TypeMapper.get_schema(source_type)

    assert schema is not None
    assert schema.type == schema_type


def test_type_mapper_register_works() -> None:
    """Ensure TypeMapper register new Schema."""
    TypeMapper.register(_TestClass, _TEST_SCHEMA)

    schema = TypeMapper.get_schema(_TestClass)
    assert schema == _TEST_SCHEMA


def test_type_mapper_register_raise_error() -> None:
    """Ensure TypeMapper raise error if register available Schema."""
    with pytest.raises(ValueError, match='already registered'):
        TypeMapper.register(int, _TEST_SCHEMA)


def test_type_mapper_override() -> None:
    """Ensure TypeMapper.override works."""
    TypeMapper.override(int, _TEST_SCHEMA)

    int_schema = TypeMapper.get_schema(int)

    assert int_schema == _TEST_SCHEMA


def test_type_mapper_typeddict() -> None:
    """Ensure TypeMapper returns None for TypedDict."""
    schema = TypeMapper.get_schema(_TestTypedDict)
    assert schema is None
