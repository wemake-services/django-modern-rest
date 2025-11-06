import pytest

try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover
    pytest.skip(reason='pydantic is not installed', allow_module_level=True)

from django_modern_rest.openapi import OpenAPIConfig
from django_modern_rest.openapi.core.context import OpenAPIContext
from django_modern_rest.openapi.extractors.base import BaseExtractor
from django_modern_rest.openapi.objects import Reference


@pytest.fixture
def context() -> OpenAPIContext:
    """Create OpenAPIContext."""
    config = OpenAPIConfig(title='Test', version='1.0.0')
    return OpenAPIContext(config)


def test_collect_schema_rejects_reference(
    context: OpenAPIContext,
) -> None:
    """Ensure that TypeError is raised when trying to collect a Reference."""
    ref = Reference(ref='#/components/schemas/SomeSchema')

    with pytest.raises(
        TypeError,
        match='Cannot register Reference object as schema',
    ):
        context.collect_schema('test', ref)


def test_collect_schema_rejects_invalid_type(
    context: OpenAPIContext,
) -> None:
    """Ensure that TypeError is raised when schema is not a Schema object."""
    with pytest.raises(
        TypeError,
        match='Expected Schema object',
    ):
        context.collect_schema('test', 'not-a-schema')


def test_get_extractor_unsupported_type_error(
    context: OpenAPIContext,
) -> None:
    """Ensure ValueError is raised when no extractor supports the type."""

    class UnsupportedType:
        """Test class."""

    with pytest.raises(
        ValueError,
        match='No schema extractor found for type',
    ):
        context.get_extractor(UnsupportedType)


def test_get_extractor_returns_correct_extractor(
    context: OpenAPIContext,
) -> None:
    """Ensure get_extractor returns extractor for supported type."""

    class TestModel(BaseModel):
        name: str

    extractor = context.get_extractor(TestModel)

    assert isinstance(extractor, BaseExtractor)
    assert extractor.supports_type(TestModel)
