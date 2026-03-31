"""Loads compiled or pure-Python negotiation implementation.

When ``mypyc`` binary wheels are installed (platform-specific wheels),
Python automatically uses the compiled ``.so`` / ``.pyd`` extension for
``dmr.internal._negotiation``.  On unsupported platforms the pure-Python
``.py`` file is used transparently - no code changes required.

Set the ``DMR_NO_BINARY`` environment variable to any non-empty value to
force the pure-Python implementation even when a compiled extension is
present (useful for debugging or comparing behaviour):

.. code-block:: console

    DMR_NO_BINARY=1 python manage.py runserver
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.internal._negotiation import (
        ConditionalType as ConditionalType,
    )
    from dmr.internal._negotiation import (
        media_by_precedence as media_by_precedence,
    )
    from dmr.internal._negotiation import (
        negotiate_renderer as negotiate_renderer,
    )
    from dmr.internal._negotiation import (
        response_validation_negotiator as response_validation_negotiator,
    )

_DMR_NO_BINARY: bool = bool(os.environ.get('DMR_NO_BINARY', ''))

if _DMR_NO_BINARY:
    import sys as _sys
    import types as _types
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    _spec = spec_from_file_location(
        'dmr.internal._negotiation_pure',
        Path(__file__).parent / '_negotiation.py',
    )
    if _spec is None or _spec.loader is None:  # pragma: no cover
        raise ImportError(
            'Failed to locate pure Python negotiation module',
        )
    _mod: _types.ModuleType = module_from_spec(_spec)
    _sys.modules['dmr.internal._negotiation_pure'] = _mod
    _spec.loader.exec_module(_mod)
    ConditionalType = _mod.ConditionalType
    response_validation_negotiator = _mod.response_validation_negotiator
    media_by_precedence = _mod.media_by_precedence
    negotiate_renderer = _mod.negotiate_renderer
else:
    from dmr.internal._negotiation import (
        ConditionalType as ConditionalType,
    )
    from dmr.internal._negotiation import (
        media_by_precedence as media_by_precedence,
    )
    from dmr.internal._negotiation import (
        negotiate_renderer as negotiate_renderer,
    )
    from dmr.internal._negotiation import (
        response_validation_negotiator as response_validation_negotiator,
    )
