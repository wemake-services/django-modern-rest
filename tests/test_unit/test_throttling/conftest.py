import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()


def pytest_collection_modifyitems(  # pragma: no cover
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],  # noqa: WPS110
) -> None:
    """Automatically run all throttling tests on a single worker."""
    # Otherwise, there can be parallel cache access / cache clear operations.
    has_xdist = os.environ.get('PYTEST_XDIST_WORKER', '')
    if not has_xdist:
        return
    for test_item in items:
        test_item.add_marker(pytest.mark.xdist_group('throttling'))
