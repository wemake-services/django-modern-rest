import sys
from collections.abc import Callable, Generator, Set
from contextlib import AbstractContextManager, contextmanager
from types import ModuleType
from typing import Final, TypeAlias

import pytest

CleanModules: TypeAlias = Callable[
    ...,
    AbstractContextManager[dict[str, ModuleType]],
]

_COMPILED_MODULES: Final = frozenset((
    'dmr.envs',
    'dmr.compiled',
    'dmr._compiled',
))


@pytest.fixture
def clean_modules() -> CleanModules:
    """Fixture to clean required modules."""

    @contextmanager
    def factory(
        names: Set[str] = _COMPILED_MODULES,
    ) -> Generator[dict[str, ModuleType]]:
        orig_modules = {}
        prefixes = tuple(f'{name}.' for name in names)
        for modname in list(sys.modules):
            if modname in names or modname.startswith(prefixes):
                orig_modules[modname] = sys.modules.pop(modname)

        try:
            yield orig_modules
        finally:
            sys.modules.update(orig_modules)

    return factory


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Automatically disable timeout for all of benchmarks."""
    for item in items:
        item.add_marker(pytest.mark.timeout(0))
