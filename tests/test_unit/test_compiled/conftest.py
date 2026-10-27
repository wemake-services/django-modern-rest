import sys
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from types import ModuleType
from typing import TypeAlias

import pytest

CleanModules: TypeAlias = Callable[
    [set[str]],
    AbstractContextManager[dict[str, ModuleType]],
]


@pytest.fixture
def clean_modules() -> CleanModules:
    """Fixture to clean required modules."""

    @contextmanager
    def factory(names: set[str]) -> Generator[dict[str, ModuleType]]:
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
