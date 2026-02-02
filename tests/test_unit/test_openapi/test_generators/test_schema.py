import pytest
from pydantic import BaseModel

from django_modern_rest.openapi.generators.schema import SchemaGenerator
from django_modern_rest.openapi.objects.reference import Reference


class _TestModel(BaseModel):
    id: int
    name: str


class _UnsupportedTestModel:
    attr: str


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
