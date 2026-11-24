import dataclasses
import re
from collections.abc import Iterator
from typing import Final, Literal, TypeAlias, final, get_args

from django.http.request import MediaType
from typing_extensions import TypeIs

from dmr.openapi.config import MIN_OPENAPI_VERSION
from dmr.openapi.mappers.schema_normalization import DumpedSchema
from dmr.openapi.objects.parameter import ParameterLocation
from dmr.openapi.objects.path_item import STANDARD_HTTP_METHODS
from dmr.types import Json

_Direction: TypeAlias = Literal['request', 'response']
_Level: TypeAlias = Literal['breaking', 'unknown']
_JsonObject: TypeAlias = dict[str, Json]
_ParameterKey: TypeAlias = tuple[str, str | int]

_PATH_PARAMETER: Final = re.compile(r'\{([^}]+)\}')
_EXTENSION_PREFIX: Final = 'x-'
_DEFAULT_STATUS: Final = 'default'
_STATUS_RANGE_SUFFIX: Final = 'XX'
_WILDCARD: Final = '*'


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
class _Node:
    """A part of the document with the JSON pointer to it."""

    spec: _JsonObject
    pointer: str
    exists: bool = True

    def child(self, key: str) -> '_Node':
        return _Node(
            spec=_section(self.spec, key),
            pointer=_join(self.pointer, key),
            exists=key in self.spec,
        )

    def elements(self, key: str) -> list['_Node']:
        found = self.spec.get(key)
        listed = found if isinstance(found, list) else ()
        return [
            _Node(spec=element, pointer=_join(self.pointer, key, index))
            for index, element in enumerate(listed)
            if isinstance(element, dict)
        ]


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Parameter:
    node: _Node
    location: ParameterLocation
    name: str
    path_names: tuple[str, ...]

    @property
    def key(self) -> _ParameterKey:
        """Path parameters are matched by position, others by name."""
        if self.location == 'path' and self.name in self.path_names:
            return self.location, self.path_names.index(self.name)
        if self.location == 'header':
            # Header names are case-insensitive:
            return self.location, self.name.lower()
        return self.location, self.name

    @property
    def label(self) -> str:
        return f'{self.location} parameter "{self.name}"'


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
    def node(self) -> _Node:
        return self._path_item_node.child(self.method)

    @property
    def request_parameters(self) -> dict[_ParameterKey, _Parameter]:
        """Operation parameters override the path item ones."""
        path_names = tuple(_PATH_PARAMETER.findall(self.path))
        return {
            parameter.key: parameter
            for owner in (self._path_item_node, self.node)
            for parameter in _described_parameters(owner, path_names)
        }

    @property
    def _path_item_node(self) -> _Node:
        return _Node(
            spec=self.path_item,
            pointer=_join('/paths', self.path),
        )


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _StatusPair:
    """Responses that old and new clients get for the same status code."""

    old: str | None
    new: str


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _ParameterChange:
    parameter: _Node
    message: str


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
        supported = tuple(map(int, major_minor)) >= MIN_OPENAPI_VERSION
    except ValueError:
        supported = False
    if not supported:
        minimum = '.'.join(map(str, MIN_OPENAPI_VERSION))
        raise ValueError(
            f'Only OpenAPI {minimum}+ schemas are supported, got {version}',
        )


def _section(node: _JsonObject, key: str) -> _JsonObject:
    found = node.get(key)
    return found if isinstance(found, dict) else {}


def _operations(document: _JsonObject) -> Iterator[_Operation]:
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


def _is_parameter_location(location: Json) -> TypeIs[ParameterLocation]:
    return location in get_args(ParameterLocation)


def _described_parameters(
    owner: _Node,
    path_names: tuple[str, ...],
) -> Iterator[_Parameter]:
    for node in owner.elements('parameters'):
        location = node.spec.get('in')
        name = node.spec.get('name')
        if _is_parameter_location(location) and isinstance(name, str):
            yield _Parameter(
                node=node,
                location=location,
                name=name,
                path_names=path_names,
            )


def _statuses(responses: _JsonObject) -> Iterator[str]:
    for status in responses:
        if not status.startswith(_EXTENSION_PREFIX):
            yield status


def _documented_status(status: str, responses: _JsonObject) -> str | None:
    """A status is also covered by its range or by the default."""
    status_class = status[:1]
    status_range = f'{status_class}{_STATUS_RANGE_SUFFIX}'
    return next(
        (
            candidate
            for candidate in (status, status_range, _DEFAULT_STATUS)
            if candidate in responses
        ),
        None,
    )


def _status_pairs(
    old_responses: _JsonObject,
    new_responses: _JsonObject,
) -> Iterator[_StatusPair]:
    for new_status in _statuses(new_responses):
        yield _StatusPair(
            old=_documented_status(new_status, old_responses),
            new=new_status,
        )
    for old_status in _statuses(old_responses):
        if old_status in new_responses:
            continue
        covering_status = _documented_status(old_status, new_responses)
        if covering_status is not None:
            yield _StatusPair(old=old_status, new=covering_status)


def _is_required(node: _Node) -> bool:
    return node.spec.get('required') is True


def _requirement_change(
    old: _Parameter | None,
    new: _Parameter,
) -> str | None:
    if not _is_required(new.node):
        return None
    if old is None:
        return f'required {new.label} added'
    if _is_required(old.node):
        return None
    return f'{new.label} became required'


def _parameter_changes(
    old: dict[_ParameterKey, _Parameter],
    new: dict[_ParameterKey, _Parameter],
) -> Iterator[_ParameterChange]:
    for key, new_parameter in new.items():
        message = _requirement_change(old.get(key), new_parameter)
        if message is not None:
            yield _ParameterChange(
                parameter=new_parameter.node,
                message=message,
            )
    for key, removed in old.items():
        if key not in new:
            yield _ParameterChange(
                parameter=removed.node,
                message=f'{removed.label} removed',
            )


def _added_status_message(status: str) -> str:
    if status == _DEFAULT_STATUS:
        return 'default response added'
    if status.endswith(_STATUS_RANGE_SUFFIX):
        return 'status code range added'
    return 'status code added'


def _media_type_parts(media_type: str) -> tuple[str, str]:
    parsed = MediaType(media_type)
    return parsed.main_type, parsed.sub_type


def _covers(media_range: str, media_type: str) -> bool:
    return all(
        range_part in {_WILDCARD, type_part}
        for range_part, type_part in zip(
            _media_type_parts(media_range),
            _media_type_parts(media_type),
            strict=True,
        )
    )


def _is_media_type_kept(
    media_type: str,
    new_content: _JsonObject,
    direction: _Direction,
) -> bool:
    """Requests can be accepted more widely, responses sent more narrowly."""
    if direction == 'request':
        return any(_covers(candidate, media_type) for candidate in new_content)
    return any(_covers(media_type, candidate) for candidate in new_content)


def _escape(key: str | int) -> str:
    return str(key).replace('~', '~0').replace('/', '~1')


def _join(pointer: str, *keys: str | int) -> str:
    return '/'.join((pointer, *map(_escape, keys)))


@final
class _Report:
    """Changes with the operations they affect."""

    __slots__ = ('_operations',)

    def __init__(self) -> None:
        self._operations: dict[Change, list[str]] = {}

    def add(
        self,
        *,
        direction: _Direction,
        location: str,
        message: str,
        operation: str,
        level: _Level = 'breaking',
    ) -> None:
        change = Change(
            level=level,
            direction=direction,
            location=f'#{location}',
            message=message,
            operations=(),
        )
        self._operations.setdefault(change, []).append(operation)

    def changes(self) -> list[Change]:
        return [
            dataclasses.replace(
                change,
                operations=tuple(dict.fromkeys(operations)),
            )
            for change, operations in self._operations.items()
        ]


@final
class _Detector:
    __slots__ = ('_new', '_old', '_report')

    def __init__(self, old: DumpedSchema, new: DumpedSchema) -> None:
        self._old = old
        self._new = new
        self._report = _Report()

    def detect(self) -> list[Change]:
        new_operations = {
            operation.key: operation for operation in _operations(self._new)
        }
        for old_operation in _operations(self._old):
            self._operation(
                old_operation,
                new_operations.get(old_operation.key),
            )
        return self._report.changes()

    def _operation(
        self,
        old_operation: _Operation,
        new_operation: _Operation | None,
    ) -> None:
        if new_operation is None:
            self._report.add(
                direction='request',
                location=old_operation.node.pointer,
                message='operation removed',
                operation=old_operation.label,
            )
            return
        self._request_parameters(old_operation, new_operation)
        self._request_body(old_operation, new_operation)
        self._responses(old_operation, new_operation)

    def _request_parameters(self, old: _Operation, new: _Operation) -> None:
        for change in _parameter_changes(
            old.request_parameters,
            new.request_parameters,
        ):
            self._report.add(
                direction='request',
                location=change.parameter.pointer,
                message=change.message,
                operation=new.label,
            )

    def _request_body(self, old: _Operation, new: _Operation) -> None:
        old_body = old.node.child('requestBody')
        new_body = new.node.child('requestBody')
        if not new_body.exists:
            if old_body.exists:
                self._report.add(
                    direction='request',
                    location=old_body.pointer,
                    message='request body removed',
                    operation=new.label,
                )
            return
        if _is_required(new_body) and not _is_required(old_body):
            message = (
                'request body became required'
                if old_body.exists
                else 'required request body added'
            )
            self._report.add(
                direction='request',
                location=new_body.pointer,
                message=message,
                operation=new.label,
            )
        self._media_types(old_body, new_body, 'request', new.label)

    def _responses(self, old: _Operation, new: _Operation) -> None:
        old_responses = old.node.child('responses')
        new_responses = new.node.child('responses')
        for pair in _status_pairs(old_responses.spec, new_responses.spec):
            new_response = new_responses.child(pair.new)
            if pair.old is None:
                self._report.add(
                    direction='response',
                    location=new_response.pointer,
                    message=_added_status_message(pair.new),
                    operation=new.label,
                )
                continue
            self._media_types(
                old_responses.child(pair.old),
                new_response,
                'response',
                new.label,
            )

    def _media_types(
        self,
        old: _Node,
        new: _Node,
        direction: _Direction,
        label: str,
    ) -> None:
        old_content = old.child('content')
        new_content = new.child('content')
        for media_type in old_content.spec:
            if not _is_media_type_kept(
                media_type,
                new_content.spec,
                direction,
            ):
                self._report.add(
                    direction=direction,
                    location=old_content.child(media_type).pointer,
                    message='media type removed',
                    operation=label,
                )
