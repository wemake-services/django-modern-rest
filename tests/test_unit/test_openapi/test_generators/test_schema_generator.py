from typing import Final

import pytest
from pydantic import BaseModel, Field

from dmr.exceptions import UnsolvableAnnotationsError
from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.schema import SchemaGenerator
from dmr.openapi.objects import OpenAPIType, Reference, Schema
from dmr.plugins.pydantic import PydanticSerializer

_MAXIMUM: Final = 100
_CONFIG: Final = OpenAPIConfig(title='Test config', version='0.1')


@pytest.fixture
def generator(openapi_context: OpenAPIContext) -> SchemaGenerator:
    """Fixture for ``SchemaGenerator`` class."""
    return openapi_context.generators.schema


class _TestModel(BaseModel):
    id: int
    name: str


class _ConstrainedModel(BaseModel):
    age: int = Field(gt=0, le=_MAXIMUM, description='User age')
    score: float = Field(default=0, ge=0, le=_MAXIMUM)


class _UnsupportedTestModel:
    attr: str


def test_schema_generator_unsupported_type(
    generator: SchemaGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure ``SchemaGenerator`` raises error."""
    with pytest.raises(
        UnsolvableAnnotationsError,
        match='_UnsupportedTestModel',
    ):
        generator(_UnsupportedTestModel, PydanticSerializer)

    openapi_context.registries.schema.register(
        _UnsupportedTestModel.__qualname__,
        Schema(type=OpenAPIType.STRING),
    )

    assert isinstance(
        generator(_UnsupportedTestModel, PydanticSerializer),
        Reference,
    )


def test_schema_generator_works(generator: SchemaGenerator) -> None:
    """Ensure ``SchemaGenerator`` generate reference."""
    ref = generator(_TestModel, PydanticSerializer)

    assert isinstance(ref, Reference)
    assert ref.ref == f'#/components/schemas/{_TestModel.__name__}'
    assert _TestModel.__name__ in generator._context.registries.schema.schemas


def test_schema_generator_caching(
    generator: SchemaGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure ``SchemaGenerator`` cache reference."""
    ref1 = generator(_TestModel, PydanticSerializer)
    ref2 = generator(_TestModel, PydanticSerializer)

    assert isinstance(ref1, Reference)
    assert isinstance(ref2, Reference)
    assert ref1.ref == ref2.ref
    assert len(openapi_context.registries.schema.schemas) == 1


def test_schema_generator_with_kwarg_definition(
    generator: SchemaGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure ``SchemaGenerator`` applies kwargs."""
    generator(_ConstrainedModel, PydanticSerializer)
    registry = openapi_context.registries.schema
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
