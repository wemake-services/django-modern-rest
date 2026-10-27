import sys
import types
from collections.abc import Mapping
from typing import TypeVar

_KeyT = TypeVar('_KeyT')
_ValueT = TypeVar('_ValueT')


def frozen(mapping: Mapping[_KeyT, _ValueT]) -> Mapping[_KeyT, _ValueT]:
    """Convert value to the frozen variant."""
    if sys.version_info < (3, 15):  # pragma: <3.15 cover
        return types.MappingProxyType(mapping)  # noqa: WPS483
    return frozendict(mapping)  # type: ignore[unreachable, name-defined, unused-ignore] # pragma: >=3.15 cover  # noqa: F821
