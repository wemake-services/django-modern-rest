import re
from typing import Any, Protocol, TypeAlias

_CapturedArgs: TypeAlias = tuple[Any, ...]
_CapturedKwargs: TypeAlias = dict[str, int | str]
_RouteMatch: TypeAlias = tuple[str, _CapturedArgs, _CapturedKwargs]


class _HasSearch(Protocol):
    @staticmethod
    def search(inp: str) -> re.Match[str] | None: ...


class _RoutePattern(Protocol):
    _is_static: bool
    _is_endpoint: bool
    _prefix: str
    converters: dict[str, Any]
    regex: _HasSearch


def match_impl(  # noqa: C901
    self: _RoutePattern,
    path: str,
) -> _RouteMatch | None:
    if self._is_static:
        if self._is_endpoint and path == self._prefix:
            return '', (), {}
        if not self._is_endpoint and path.startswith(self._prefix):
            return path[len(self._prefix) :], (), {}
    elif path.startswith(self._prefix):
        match = self.regex.search(path)
        if match:
            # RoutePattern doesn't allow non-named groups so args are ignored.
            kwargs = match.groupdict()
            for key, value in kwargs.items():
                converter = self.converters[key]
                try:
                    kwargs[key] = converter.to_python(value)
                except ValueError:
                    return None
            return path[match.end() :], (), kwargs
    return None
