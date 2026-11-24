import dataclasses
import re
from collections.abc import Iterator
from typing import Final, Literal, TypeAlias, final, get_args
from urllib.parse import quote, unquote

from django.http.request import MediaType
from typing_extensions import TypeIs

try:
    import jsonschema_rs
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `jsonschema-rs` is not installed, '
        "consider using `pip install 'django-modern-rest[openapi]'`",
    )
    raise

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
_SCHEMA_KEYWORDS: Final = ('schema', 'itemSchema')
_OLD_URI: Final = 'urn:dmr:old'
_NEW_URI: Final = 'urn:dmr:new'
_DRAFT: Final = jsonschema_rs.Draft202012
_Containment: Final = jsonschema_rs.canonical.Containment


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
    resolver: jsonschema_rs.Resolver
    exists: bool = True

    def child(self, key: str) -> '_Node':
        return _Node(
            spec=_as_object(self.spec.get(key)),
            pointer=_join(self.pointer, key),
            resolver=self.resolver,
            exists=key in self.spec,
        )

    def elements(self, key: str) -> list['_Node']:
        found = self.spec.get(key)
        listed = found if isinstance(found, list) else ()
        return [
            _Node(
                spec=element,
                pointer=_join(self.pointer, key, index),
                resolver=self.resolver,
            )
            for index, element in enumerate(listed)
            if isinstance(element, dict)
        ]

    def referenced(self, key: str) -> '_Node':
        return self.child(key).resolved()

    def resolved(self) -> '_Node':
        """Follows references to other parts of the document."""
        reference = self.spec.get('$ref')
        if not isinstance(reference, str):
            return self
        found = self.resolver.lookup(reference)
        _, _, fragment = reference.partition('#')
        return _Node(
            spec=_as_object(found.contents),
            pointer=unquote(fragment),
            resolver=found.resolver,
        ).resolved()


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
    node: _Node
    path_items: tuple[_Node, ...]

    @property
    def key(self) -> tuple[str, str]:
        """Path parameters can be renamed freely."""
        return _PATH_PARAMETER.sub('{}', self.path), self.method

    @property
    def label(self) -> str:
        verb = self.method.upper()
        return f'{verb} {self.path}'

    @property
    def request_parameters(self) -> dict[_ParameterKey, _Parameter]:
        """Operation parameters override the path item ones."""
        path_names = tuple(_PATH_PARAMETER.findall(self.path))
        return {
            parameter.key: parameter
            for owner in (*self.path_items, self.node)
            for parameter in _described_parameters(owner, path_names)
        }


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _StatusPair:
    """Responses that old and new clients get for the same status code."""

    old: str | None
    new: str


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Finding:
    location: str
    message: str
    level: _Level = 'breaking'


@final
class _SchemaComparison:
    """Compares JSON Schemas as sets of values they accept."""

    __slots__ = ('_canonical', '_registry')

    def __init__(self, registry: jsonschema_rs.Registry) -> None:
        self._registry = registry
        self._canonical: dict[str, jsonschema_rs.CanonicalSchema] = {}

    def findings(
        self,
        old_owner: _Node,
        new_owner: _Node,
        direction: _Direction,
    ) -> Iterator[_Finding]:
        """Schemas missing on either side are not compared."""
        for keyword in _SCHEMA_KEYWORDS:
            old_schema = old_owner.child(keyword)
            new_schema = new_owner.child(keyword)
            if not (old_schema.exists and new_schema.exists):
                continue
            level = self._level(old_schema, new_schema, direction)
            if level is not None:
                yield _Finding(
                    location=new_schema.pointer,
                    message=_schema_message(level, direction),
                    level=level,
                )

    def _level(
        self,
        old_schema: _Node,
        new_schema: _Node,
        direction: _Direction,
    ) -> _Level | None:
        try:
            containment = self._containment(old_schema, new_schema, direction)
        except jsonschema_rs.canonical.CanonicalizationError:
            return 'unknown'
        if containment == _Containment.YES:
            return None
        return 'breaking' if containment == _Containment.NO else 'unknown'

    def _containment(
        self,
        old_schema: _Node,
        new_schema: _Node,
        direction: _Direction,
    ) -> jsonschema_rs.canonical.Containment:
        """Requests must stay accepted, responses must stay expected."""
        old_accepted = self._canonicalize(old_schema)
        new_accepted = self._canonicalize(new_schema)
        if direction == 'request':
            return new_accepted.covers(old_accepted)
        return old_accepted.covers(new_accepted)

    def _canonicalize(self, schema: _Node) -> jsonschema_rs.CanonicalSchema:
        base_uri = schema.resolver.base_uri
        fragment = quote(schema.pointer, safe='/~')
        reference = f'{base_uri}#{fragment}'
        if reference not in self._canonical:
            self._canonical[reference] = jsonschema_rs.canonicalize(
                {'$ref': reference},
                registry=self._registry,
                draft=_DRAFT,
                validate_formats=True,
            )
        return self._canonical[reference]


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


def _is_object(found: object) -> TypeIs[_JsonObject]:
    return isinstance(found, dict)


def _as_object(found: object) -> _JsonObject:
    return found if _is_object(found) else {}


def _root(document: DumpedSchema, resolver: jsonschema_rs.Resolver) -> _Node:
    return _Node(spec=document, pointer='', resolver=resolver)


def _path_items(written: _Node) -> tuple[_Node, ...]:
    """Fields can be written next to a reference to another path item."""
    target = written.resolved()
    return (written,) if target is written else (written, target)


def _operations(document: _Node) -> Iterator[_Operation]:
    paths = document.child('paths')
    for path in paths.spec:
        path_items = _path_items(paths.child(path))
        for path_item in path_items:
            for method in path_item.spec:
                if method in STANDARD_HTTP_METHODS:
                    yield _Operation(
                        path=path,
                        method=method,
                        node=path_item.child(method),
                        path_items=path_items,
                    )


def _is_parameter_location(location: Json) -> TypeIs[ParameterLocation]:
    return location in get_args(ParameterLocation)


def _described_parameters(
    owner: _Node,
    path_names: tuple[str, ...],
) -> Iterator[_Parameter]:
    for element in owner.elements('parameters'):
        node = element.resolved()
        location = node.spec.get('in')
        name = node.spec.get('name')
        # Narrows types, the specification requires both fields:
        if (  # pragma: no branch
            _is_parameter_location(location) and isinstance(name, str)
        ):
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
    schemas: _SchemaComparison,
) -> Iterator[_Finding]:
    for key, new_parameter in new.items():
        old_parameter = old.get(key)
        message = _requirement_change(old_parameter, new_parameter)
        if message is not None:
            yield _Finding(
                location=new_parameter.node.pointer,
                message=message,
            )
        if old_parameter is not None:
            yield from schemas.findings(
                old_parameter.node,
                new_parameter.node,
                'request',
            )
    for key, removed in old.items():
        if key not in new:
            yield _Finding(
                location=removed.node.pointer,
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


def _is_kept_as(media_type: str, candidate: str, direction: _Direction) -> bool:
    """Requests can be accepted more widely, responses sent more narrowly."""
    if direction == 'request':
        return _covers(candidate, media_type)
    return _covers(media_type, candidate)


def _media_type_changes(
    old_content: _Node,
    new_content: _Node,
    direction: _Direction,
    schemas: _SchemaComparison,
) -> Iterator[_Finding]:
    for media_type in old_content.spec:
        old_media = old_content.referenced(media_type)
        kept = [
            candidate
            for candidate in new_content.spec
            if _is_kept_as(media_type, candidate, direction)
        ]
        if not kept:
            yield _Finding(
                location=old_media.pointer,
                message='media type removed',
            )
        for new_media_type in kept:
            yield from schemas.findings(
                old_media,
                new_content.referenced(new_media_type),
                direction,
            )


def _schema_message(level: _Level, direction: _Direction) -> str:
    if level == 'unknown':
        return 'schema changed'
    if direction == 'request':
        return 'schema accepts fewer values'
    return 'schema allows more values'


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
        finding: _Finding,
        *,
        direction: _Direction,
        operation: str,
    ) -> None:
        change = Change(
            level=finding.level,
            direction=direction,
            location=f'#{finding.location}',
            message=finding.message,
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
    __slots__ = ('_new', '_old', '_report', '_schemas')

    def __init__(self, old: DumpedSchema, new: DumpedSchema) -> None:
        registry = jsonschema_rs.Registry(
            [(_OLD_URI, old), (_NEW_URI, new)],
            draft=_DRAFT,
        )
        self._old = _root(old, registry.resolver(_OLD_URI))
        self._new = _root(new, registry.resolver(_NEW_URI))
        self._report = _Report()
        self._schemas = _SchemaComparison(registry)

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
                _Finding(
                    location=old_operation.node.pointer,
                    message='operation removed',
                ),
                direction='request',
                operation=old_operation.label,
            )
            return
        self._request_parameters(old_operation, new_operation)
        self._request_body(old_operation, new_operation)
        self._responses(old_operation, new_operation)

    def _request_parameters(self, old: _Operation, new: _Operation) -> None:
        for finding in _parameter_changes(
            old.request_parameters,
            new.request_parameters,
            self._schemas,
        ):
            self._report.add(
                finding,
                direction='request',
                operation=new.label,
            )

    def _request_body(self, old: _Operation, new: _Operation) -> None:
        old_body = old.node.referenced('requestBody')
        new_body = new.node.referenced('requestBody')
        if not new_body.exists:
            if old_body.exists:
                self._report.add(
                    _Finding(
                        location=old_body.pointer,
                        message='request body removed',
                    ),
                    direction='request',
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
                _Finding(location=new_body.pointer, message=message),
                direction='request',
                operation=new.label,
            )
        self._media_types(old_body, new_body, 'request', new.label)

    def _responses(self, old: _Operation, new: _Operation) -> None:
        old_responses = old.node.child('responses')
        new_responses = new.node.child('responses')
        for pair in _status_pairs(old_responses.spec, new_responses.spec):
            new_response = new_responses.referenced(pair.new)
            if pair.old is None:
                self._report.add(
                    _Finding(
                        location=new_response.pointer,
                        message=_added_status_message(pair.new),
                    ),
                    direction='response',
                    operation=new.label,
                )
                continue
            self._media_types(
                old_responses.referenced(pair.old),
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
        for finding in _media_type_changes(
            old.child('content'),
            new.child('content'),
            direction,
            self._schemas,
        ):
            self._report.add(finding, direction=direction, operation=label)
