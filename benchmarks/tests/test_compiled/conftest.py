import sys
from collections.abc import Callable, Iterator, Set
from contextlib import AbstractContextManager, contextmanager
from types import ModuleType
from typing import Final, TypeAlias

import pytest

CleanModules: TypeAlias = Callable[
    [],
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
    ) -> Iterator[dict[str, ModuleType]]:
        orig_modules = {}
        prefixes = tuple(f'{name}.' for name in names)
        for modname in list(sys.modules):
            if modname in names or modname.startswith(prefixes):
                orig_modules[modname] = sys.modules.pop(modname)

        yield orig_modules

        sys.modules.update(orig_modules)

    return factory
