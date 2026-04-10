import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()
