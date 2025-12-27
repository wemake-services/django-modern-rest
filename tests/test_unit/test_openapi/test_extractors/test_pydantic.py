from typing import Any

import pytest

try:
    import pydantic  # noqa: F401
except ImportError:  # pragma: no cover
    pytest.skip(reason='pydantic is not installed', allow_module_level=True)

from django_modern_rest.openapi import OpenAPIConfig
from django_modern_rest.openapi.core.context import OpenAPIContext
from django_modern_rest.openapi.extractors.pydantic import PydanticExtractor
from django_modern_rest.openapi.objects import Schema


@pytest.fixture
def extractor() -> PydanticExtractor:
    """Create PydanticExtractor."""
    config = OpenAPIConfig(title='Test', version='1.0.0')
    context = OpenAPIContext(config)
    return PydanticExtractor(context)


def test_supports_type_with_unsupported_type(
    extractor: PydanticExtractor,
) -> None:
    """Ensure supports_type returns False for unsupported types."""

    class UnsupportedType:
        """A type that Pydantic cannot adapt."""

    is_support_type = extractor.supports_type(UnsupportedType)

    assert is_support_type is False


def test_supports_type_with_invalid_complex_type(
    extractor: PydanticExtractor,
) -> None:
    """Ensure supports_type returns False for invalid complex types."""
    invalid_type: Any = object()

    is_support_type = extractor.supports_type(invalid_type)

    assert is_support_type is False


def test_convert_json_schema_with_all_of(extractor: PydanticExtractor) -> None:
    """Ensure _convert_json_schema handles allOf correctly."""
    json_schema = {
        'allOf': [
            {'type': 'string'},
            {'type': 'object', 'properties': {'name': {'type': 'string'}}},
        ],
    }

    schema = extractor._convert_json_schema(json_schema)  # noqa: SLF001

    assert isinstance(schema, Schema)
    assert schema.all_of is not None
    assert len(schema.all_of) == 2


def test_convert_json_schema_with_one_of(extractor: PydanticExtractor) -> None:
    """Ensure _convert_json_schema handles oneOf correctly."""
    json_schema = {
        'oneOf': [
            {'type': 'string'},
            {'type': 'object', 'properties': {'name': {'type': 'string'}}},
        ],
    }

    schema = extractor._convert_json_schema(json_schema)  # noqa: SLF001

    assert isinstance(schema, Schema)
    assert schema.one_of is not None
    assert len(schema.one_of) == 2
