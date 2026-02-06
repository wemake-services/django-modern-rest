from typing import Final

import pytest

from django_modern_rest.openapi.objects.enums import OpenAPIType
from django_modern_rest.openapi.objects.schema import Schema
from django_modern_rest.openapi.type_mapping import TypeMapper


class _TestClass:
    attr: int


_TEST_SCHEMA: Final = Schema(type=OpenAPIType.OBJECT)


def test_type_mapper_get_type() -> None:
    """Ensure TypeMapper get_type works."""
    int_schema = TypeMapper.get_schema(int)

    assert int_schema is not None
    assert int_schema.type == OpenAPIType.INTEGER


def test_type_mapper_register_works() -> None:
    """Ensure TypeMapper register new Schema."""
    TypeMapper.register(_TestClass, _TEST_SCHEMA)

    assert _TestClass in TypeMapper._type_map


def test_type_mapper_register_raise_error() -> None:
    """Ensure TypeMapper raise error if register available Schema."""
    with pytest.raises(ValueError, match='already registered'):
        TypeMapper.register(int, _TEST_SCHEMA)


def test_type_mapper_override() -> None:
    """Ensure TypeMapper.override works."""
    TypeMapper.override(int, _TEST_SCHEMA)

    int_schema = TypeMapper.get_schema(int)

    assert int_schema == _TEST_SCHEMA
