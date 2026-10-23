import sys
import types
from collections.abc import Mapping
from typing import TypeVar

if sys.version_info >= (3, 15):
    # This is needed to `ruff` and others to work:
    from builtins import frozendict

_KeyT = TypeVar('_KeyT')
_ValueT = TypeVar('_ValueT')


def frozen(mapping: Mapping[_KeyT, _ValueT]) -> Mapping[_KeyT, _ValueT]:
    """Convert value to the frozen variant."""
    if sys.version_info >= (3, 15):  # pragma: >=3.15 cover
        return frozendict(mapping)
    return types.MappingProxyType(mapping)  # noqa: WPS483  # pragma: <3.15 cover
