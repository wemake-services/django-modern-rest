from collections.abc import Generator

import pytest

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.mappers.types import TypeMapper


@pytest.fixture(autouse=True)
def reset_type_mapper() -> Generator[None, None, None]:
    """Reset ``TypeMapper._type_map`` after each test."""
    original_map = TypeMapper._mapping.copy()
    yield
    TypeMapper._mapping = original_map


@pytest.fixture
def openapi_context() -> OpenAPIContext:
    """Returns OpenAPI context for the spec tests."""
    return OpenAPIContext(OpenAPIConfig(title='tests', version='0.0.1'))
