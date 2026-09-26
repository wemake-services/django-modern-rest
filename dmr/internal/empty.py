from typing import Final

from typing_extensions import Sentinel

# NOTE: this module must not import anything from `dmr`,
# so it can be used anywhere without creating import cycles.

#: Default singleton for empty values, re-exported as ``dmr.types.EMPTY``.
EMPTY: Final = Sentinel('EMPTY')
