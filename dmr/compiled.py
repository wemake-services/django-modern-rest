from typing import TYPE_CHECKING

from dmr.envs import USE_COMPILED

if TYPE_CHECKING:
    from dmr._compiled.negotiation import accepted_type as accepted_type

if USE_COMPILED:
    from dmr._compiled.negotiation import accepted_type  # noqa: WPS474
else:
    import sys
    import types

    def _import_pure(submodule: str) -> types.ModuleType:
        from importlib.util import (  # noqa: PLC0415
            module_from_spec,
            spec_from_file_location,
        )
        from pathlib import Path  # noqa: PLC0415

        submodule_name = f'dmr._compiled._{submodule}_pure'

        spec = spec_from_file_location(
            submodule_name,
            Path(__file__).parent / '_compiled' / f'{submodule}.py',
        )
        if spec is None or spec.loader is None:  # pragma: no cover
            raise ImportError(
                f'Failed to locate pure Python {submodule} module',
            )
        mod = module_from_spec(spec)
        sys.modules[submodule_name] = mod
        spec.loader.exec_module(mod)

        return mod

    # Add new objects here:
    _mod = _import_pure('negotiation')
    accepted_type = _mod.accepted_type

    del sys, types, _import_pure, _mod  # noqa: WPS420
