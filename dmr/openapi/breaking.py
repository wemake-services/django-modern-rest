import dataclasses
import re
from collections.abc import Iterator
from typing import Final, Literal, TypeAlias, final

from dmr.openapi.mappers.schema_normalization import DumpedSchema
from dmr.openapi.objects.path_item import STANDARD_HTTP_METHODS

_Direction: TypeAlias = Literal['request', 'response']
_Level: TypeAlias = Literal['breaking', 'unknown']
_JsonScalar: TypeAlias = str | float | bool | None
_Json: TypeAlias = dict[str, '_Json'] | list['_Json'] | _JsonScalar
_JsonObject: TypeAlias = dict[str, _Json]

_PATH_PARAMETER: Final = re.compile(r'\{([^}]+)\}')


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Change:
    """
    A change that old API clients might not survive.

    Attributes:
        level: ``'breaking'`` when the change is proven to break clients,
            ``'unknown'`` when it can't be proven either way.
        direction: Whether requests or responses are affected.
        location: JSON pointer to the smallest changed part of the schema.
        message: What has changed.
        operations: Affected API operations.

    .. versionadded:: 0.18.0

    """

    level: _Level
    direction: _Direction
    location: str
    message: str
    operations: tuple[str, ...]


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Operation:
    path: str
    method: str
    path_item: _JsonObject

    @property
    def key(self) -> tuple[str, str]:
        """Path parameters can be renamed freely."""
        return _PATH_PARAMETER.sub('{}', self.path), self.method

    @property
    def label(self) -> str:
        verb = self.method.upper()
        return f'{verb} {self.path}'

    @property
    def pointer(self) -> str:
        return _join('/paths', self.path, self.method)


def find_breaking_changes(
    old: DumpedSchema,
    new: DumpedSchema,
) -> list[Change]:
    """
    Find changes in the new OpenAPI schema that break the old API clients.

    Raises:
        ValueError: if any schema is older than OpenAPI ``'3.1.0'``.

    .. versionadded:: 0.18.0

    """
    for document in (old, new):
        _validate_version(document)
    return _Detector(old, new).detect()


def _validate_version(document: DumpedSchema) -> None:
    version = str(document.get('openapi'))
    major_minor = version.split('.')[:2]
    try:
        supported = tuple(map(int, major_minor)) >= (3, 1)
    except ValueError:
        supported = False
    if not supported:
        raise ValueError(
            f'Only OpenAPI 3.1+ schemas are supported, got {version}',
        )


def _section(node: _JsonObject, key: str) -> _JsonObject:
    found = node.get(key)
    return found if isinstance(found, dict) else {}


def _escape(key: str | int) -> str:
    return str(key).replace('~', '~0').replace('/', '~1')


def _join(pointer: str, *keys: str | int) -> str:
    return '/'.join((pointer, *map(_escape, keys)))


@final
class _Detector:
    __slots__ = ('_changes', '_new', '_old')

    def __init__(self, old: DumpedSchema, new: DumpedSchema) -> None:
        self._old = old
        self._new = new
        # Changes without operations, with the operations they affect:
        self._changes: dict[Change, list[str]] = {}

    def detect(self) -> list[Change]:
        new_operations = {
            operation.key: operation
            for operation in self._operations(self._new)
        }
        for old_operation in self._operations(self._old):
            self._operation(
                old_operation,
                new_operations.get(old_operation.key),
            )
        return [
            dataclasses.replace(
                change,
                operations=tuple(dict.fromkeys(operations)),
            )
            for change, operations in self._changes.items()
        ]

    def _operation(
        self,
        old_operation: _Operation,
        new_operation: _Operation | None,
    ) -> None:
        if new_operation is None:
            self._add(
                'breaking',
                'request',
                old_operation.pointer,
                'operation removed',
                old_operation.label,
            )

    def _add(
        self,
        level: _Level,
        direction: _Direction,
        location: str,
        message: str,
        operation: str,
    ) -> None:
        change = Change(
            level=level,
            direction=direction,
            location=f'#{location}',
            message=message,
            operations=(),
        )
        self._changes.setdefault(change, []).append(operation)

    def _operations(self, document: _JsonObject) -> Iterator[_Operation]:
        paths = _section(document, 'paths')
        for path in paths:
            path_item = _section(paths, path)
            for method in path_item:
                if method in STANDARD_HTTP_METHODS:
                    yield _Operation(
                        path=path,
                        method=method,
                        path_item=path_item,
                    )
