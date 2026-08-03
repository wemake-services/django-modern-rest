import pytest


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically disable timeout for all of benchmarks"""
    for item in items:
        item.add_marker(pytest.mark.timeout(0))
