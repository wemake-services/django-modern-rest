from collections.abc import Generator

import pytest

from django_modern_rest.openapi.type_mapping import TypeMapper


@pytest.fixture(autouse=True)
def reset_type_mapper() -> Generator[None, None, None]:
    """Reset TypeMapper._type_map after each test."""
    original_map = TypeMapper._type_map.copy()
    yield
    TypeMapper._type_map = original_map
