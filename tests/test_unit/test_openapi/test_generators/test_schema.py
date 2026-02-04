from types import NoneType
from typing import Final, TypedDict

import pytest
from pydantic import BaseModel, Field

from django_modern_rest.openapi.generators.schema import (
    _TYPE_MAP,
    SchemaGenerator,
    _handle_sequence,
    _handle_union,
)
from django_modern_rest.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.schema import Schema
from django_modern_rest.openapi.types import KwargDefinition
from django_modern_rest.plugins import pydantic  # noqa: F401

_MAXIMUM: Final = 100


class _TestModel(BaseModel):
    id: int
    name: str


class _ConstrainedModel(BaseModel):
    age: int = Field(gt=0, le=_MAXIMUM, description='User age')
    score: float = Field(default=0, ge=0, le=_MAXIMUM)


class _UnsupportedTestModel:
    attr: str


class _TestTypedDict(TypedDict):
    attr: int


def test_schema_generator_unsupported_type() -> None:
    """Ensure SchemaGenerator raises error."""
    generator = SchemaGenerator()
    with pytest.raises(ValueError, match=r'Field extractor for .* not found'):
        generator.generate(_UnsupportedTestModel)


def test_schema_generator_works() -> None:
    """Ensure SchemaGenerator generate reference."""
    generator = SchemaGenerator()

    ref = generator.generate(_TestModel)

    assert isinstance(ref, Reference)
    assert ref.ref == f'#/components/schemas/{_TestModel.__name__}'
    assert _TestModel.__name__ in generator.registry.schemas


def test_schema_generator_caching() -> None:
    """Ensure SchemaGenerator cache reference."""
    generator = SchemaGenerator()

    ref1 = generator.generate(_TestModel)
    ref2 = generator.generate(_TestModel)

    assert ref1.ref == ref2.ref
    assert len(generator.registry.schemas) == 1


def test_handle_sequence_without_args() -> None:
    """Ensure _handle_sequence handles bare sequence types."""
    generator = SchemaGenerator()

    schema = _handle_sequence(generator, ())

    assert schema.type == OpenAPIType.ARRAY
    assert schema.items is None


def test_schema_generator_with_kwarg_definition() -> None:
    """Ensure SchemaGenerator applies KwargDefinition."""
    generator = SchemaGenerator()

    generator.generate(_ConstrainedModel)
    schema = generator.registry.schemas[_ConstrainedModel.__name__]

    assert schema.properties is not None
    age_schema = schema.properties['age']
    assert isinstance(age_schema, Schema)
    assert age_schema.exclusive_minimum == 0
    assert age_schema.maximum == _MAXIMUM
    assert age_schema.description == 'User age'

    score_schema = schema.properties['score']
    assert isinstance(score_schema, Schema)
    assert score_schema.default == 0
    assert score_schema.minimum == 0
    assert score_schema.maximum == _MAXIMUM


def test_schema_generator_typed_dict() -> None:
    """Ensure SchemaGenerator handles TypedDict correctly."""
    generator = SchemaGenerator()

    ref = generator.generate(_TestTypedDict)

    assert isinstance(ref, Reference)
    assert ref.ref == f'#/components/schemas/{_TestTypedDict.__name__}'

    registered_schema = generator.registry.schemas[_TestTypedDict.__name__]
    assert isinstance(registered_schema, Schema)
    assert registered_schema.type == OpenAPIType.OBJECT
    assert registered_schema.properties is not None
    assert 'attr' in registered_schema.properties


def test_handle_union_only_none() -> None:
    """Ensure _handle_union handles Union of only None types."""
    generator = SchemaGenerator()

    schema = _handle_union(generator, (NoneType, type(None)))

    assert schema is _TYPE_MAP[NoneType]
    assert isinstance(schema, Schema)
    assert schema.type == OpenAPIType.NULL


def test_apply_kwarg_definition_format() -> None:
    """Ensure _apply_kwarg_definition handles format correctly."""
    generator = SchemaGenerator()
    schema = Schema(type=OpenAPIType.STRING)
    kwarg_def = KwargDefinition(format='ipv4')

    updated_schema = generator._apply_kwarg_definition(schema, kwarg_def)

    assert isinstance(updated_schema, Schema)
    assert updated_schema.format == OpenAPIFormat.IPV4
