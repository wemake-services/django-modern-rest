import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Automatically run all throttling tests on a single worker."""
    # Otherwise, there can be parallel cache access / cache clear operations.
    for item in items:
        item.add_marker(pytest.mark.xdist_group('throttling'))
