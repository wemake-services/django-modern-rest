from typing import Final

import pytest

from dmr.openapi.breaking import Change, find_breaking_changes
from dmr.openapi.mappers.schema_normalization import DumpedSchema

_INTEGER: Final[DumpedSchema] = {'type': 'integer'}  # noqa: WPS407


def _operation(
    *,
    parameters: list[DumpedSchema] | None = None,  # noqa: WPS110
) -> DumpedSchema:
    operation: DumpedSchema = {'responses': {'200': {'description': 'ok'}}}
    if parameters is not None:
        operation['parameters'] = parameters
    return operation


def _spec(paths: DumpedSchema) -> DumpedSchema:
    return {
        'openapi': '3.1.0',
        'info': {'title': 'test', 'version': '1'},
        'paths': paths,
    }


@pytest.mark.parametrize(
    ('old', 'new'),
    [
        (
            _spec({'/users': {'get': _operation()}}),
            _spec({'/users': {'get': _operation(), 'post': _operation()}}),
        ),
        # Not everything in a path item is an operation:
        (
            _spec({'/users': {'summary': 'Users', 'get': _operation()}}),
            _spec({'/users': {'get': _operation()}}),
        ),
        (
            _spec({
                '/users/{id}': {
                    'get': _operation(
                        parameters=[
                            {
                                'name': 'id',
                                'in': 'path',
                                'required': True,
                                'schema': _INTEGER,
                            },
                        ],
                    ),
                },
            }),
            _spec({
                '/users/{user_id}': {
                    'get': _operation(
                        parameters=[
                            {
                                'name': 'user_id',
                                'in': 'path',
                                'required': True,
                                'schema': _INTEGER,
                            },
                        ],
                    ),
                },
            }),
        ),
    ],
)
def test_compatible(*, old: DumpedSchema, new: DumpedSchema) -> None:
    """Ensures that compatible changes are not reported."""
    assert find_breaking_changes(old, new) == []


def _change(location: str, message: str) -> Change:
    return Change(
        level='breaking',
        direction='request',
        location=location,
        message=message,
        operations=('POST /users',),
    )


@pytest.mark.parametrize(
    ('old', 'new', 'expected'),
    [
        (
            _spec({'/users': {'get': _operation(), 'post': _operation()}}),
            _spec({'/users': {'get': _operation()}}),
            [_change('#/paths/~1users/post', 'operation removed')],
        ),
        (
            _spec({'/users': {'post': _operation()}}),
            _spec({}),
            [_change('#/paths/~1users/post', 'operation removed')],
        ),
    ],
)
def test_breaking(
    *,
    old: DumpedSchema,
    new: DumpedSchema,
    expected: list[Change],
) -> None:
    """Ensures that breaking changes are reported where they happen."""
    assert find_breaking_changes(old, new) == expected


@pytest.mark.parametrize('version', ['3.0.3', '2.0', None])
def test_unsupported_version(*, version: str | None) -> None:
    """Ensures that only OpenAPI 3.1+ is supported."""
    with pytest.raises(ValueError, match=r'3\.1'):
        find_breaking_changes({'openapi': version}, _spec({}))
