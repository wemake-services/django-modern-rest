from types import NoneType
from typing import Final

import pytest
from pydantic import BaseModel, Field

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.schema import (
    SchemaGenerator,
    _handle_sequence,
    _handle_union,
)
from dmr.openapi.mappers import KwargMapper, TypeMapper
from dmr.openapi.objects.enums import OpenAPIFormat, OpenAPIType
from dmr.openapi.objects.reference import Reference
from dmr.openapi.objects.schema import Schema
from dmr.openapi.types import FieldDefinition, KwargDefinition
from dmr.plugins import pydantic  # noqa: F401

_MAXIMUM: Final = 100
_CONFIG: Final = OpenAPIConfig(title='Test config', version='0.1')


@pytest.fixture
def generator() -> SchemaGenerator:
    """Create ``SchemaGenerator`` instance for testing."""
    context = OpenAPIContext(config=_CONFIG)
    return context.generators.schema


class _TestModel(BaseModel):
    id: int
    name: str


class _ConstrainedModel(BaseModel):
    age: int = Field(gt=0, le=_MAXIMUM, description='User age')
    score: float = Field(default=0, ge=0, le=_MAXIMUM)


class _UnsupportedTestModel:
    attr: str


class _NamedModel(BaseModel):
    __dmr_schema_name__ = 'SchemaName'


def test_schema_generator_unsupported_type(generator: SchemaGenerator) -> None:
    """Ensure ``SchemaGenerator`` raises error."""
    with pytest.raises(ValueError, match=r'Field extractor for .* not found'):
        generator(_UnsupportedTestModel)


def test_schema_generator_works(generator: SchemaGenerator) -> None:
    """Ensure ``SchemaGenerator`` generate reference."""
    ref = generator(_TestModel)

    assert isinstance(ref, Reference)
    assert ref.ref == f'#/components/schemas/{_TestModel.__name__}'
    assert _TestModel.__name__ in generator._context.registries.schema.schemas


def test_schema_generator_caching(generator: SchemaGenerator) -> None:
    """Ensure ``SchemaGenerator`` cache reference."""
    ref1 = generator(_TestModel)
    ref2 = generator(_TestModel)

    assert isinstance(ref1, Reference)
    assert isinstance(ref2, Reference)
    assert ref1.ref == ref2.ref
    assert len(generator._context.registries.schema.schemas) == 1


def test_handle_sequence_without_args(generator: SchemaGenerator) -> None:
    """Ensure ``_handle_sequence`` handles bare sequence types."""
    schema = _handle_sequence(generator, ())

    assert schema.type == OpenAPIType.ARRAY
    assert schema.items is None


def test_schema_generator_with_kwarg_definition(
    generator: SchemaGenerator,
) -> None:
    """Ensure ``SchemaGenerator`` applies ``KwargDefinition``."""
    generator(_ConstrainedModel)
    registry = generator._context.registries.schema
    schema = registry.schemas[_ConstrainedModel.__name__]

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


def test_handle_union_only_none(generator: SchemaGenerator) -> None:
    """Ensure ``_handle_union`` handles ``Union`` of only ``None`` types."""
    schema = _handle_union(generator, (NoneType, type(None)))

    assert schema is TypeMapper.get_schema(NoneType)
    assert isinstance(schema, Schema)
    assert schema.type == OpenAPIType.NULL


def test_extract_properties_wo_kwarg_definition(
    generator: SchemaGenerator,
) -> None:
    """Ensure ``_extract_properties`` works ``kwarg_definition``."""
    field_def = FieldDefinition(
        name='test_field',
        annotation=int,
        kwarg_definition=None,
    )
    props, _ = generator._extract_properties(
        [field_def],
        KwargMapper(),
    )

    assert 'test_field' in props
    assert isinstance(props['test_field'], Schema)
    assert props['test_field'].type == OpenAPIType.INTEGER


def test_apply_kwarg_definition_format(generator: SchemaGenerator) -> None:
    """Ensure ``_apply_kwarg_definition`` handles format correctly."""
    updated_schema = generator._apply_kwarg_definition(
        Schema(type=OpenAPIType.STRING),
        KwargDefinition(format='ipv4'),
        KwargMapper(),
    )

    assert isinstance(updated_schema, Schema)
    assert updated_schema.format == OpenAPIFormat.IPV4


def test_get_schema_name(generator: SchemaGenerator) -> None:
    """Ensure ``_get_schema_name`` returns a given schema name if one exists."""
    name = generator._get_schema_name(_NamedModel)
    assert name == _NamedModel.__dmr_schema_name__
