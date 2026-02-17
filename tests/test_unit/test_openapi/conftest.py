from collections.abc import Generator

import pytest

from dmr.openapi.mappers import TypeMapper


@pytest.fixture(autouse=True)
def reset_type_mapper() -> Generator[None, None, None]:
    """Reset ``TypeMapper._type_map`` after each test."""
    original_map = TypeMapper._mapping.copy()
    yield
    TypeMapper._mapping = original_map
