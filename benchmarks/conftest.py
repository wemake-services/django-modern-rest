import pytest

def pytest_collection_modifyitems(items):
    """Automatically disable timeout for all of benchmarks"""
    for item in items:
        item.add_marker(pytest.mark.timeout(0))
