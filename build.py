"""Poetry build hook: optionally compile ``dmr/internal/_negotiation.py``.

Compiles with ``mypyc`` when the ``DMR_USE_MYPYC`` environment variable
is set.

Usage (build a binary wheel locally)::

    DMR_USE_MYPYC=1 pip wheel .

The GitHub Actions ``build_wheels`` workflow sets this variable
automatically via cibuildwheel.
"""

from __future__ import annotations

import os
from typing import Any


def build(setup_kwargs: dict[str, Any]) -> None:
    """Compile hot-path module with mypyc when DMR_USE_MYPYC is set."""
    if not os.environ.get('DMR_USE_MYPYC'):
        return
    from mypyc.build import mypycify  # noqa: PLC0415

    setup_kwargs['ext_modules'] = mypycify(
        ['dmr/internal/_negotiation.py'],
        opt_level='3',
    )
