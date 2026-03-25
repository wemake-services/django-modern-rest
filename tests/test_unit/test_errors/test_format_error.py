from http import HTTPStatus
from typing import Any

import pytest
from django.conf import LazySettings
from django.utils.encoding import force_str

from dmr.errors import ErrorType, format_error
from dmr.exceptions import (
    InternalServerError,
    NotAcceptableError,
    NotAuthenticatedError,
    RequestSerializationError,
    ResponseSchemaError,
    ValidationError,
)


@pytest.mark.parametrize(
    ('input_args', 'expected'),
    [
        (
            (('something went wrong',), {}),
            {'detail': [{'msg': 'something went wrong'}]},
        ),
        (
            (('bad value',), {'loc': 'body'}),
            {'detail': [{'msg': 'bad value', 'loc': ['body']}]},
        ),
        (
            (('bad value',), {'error_type': ErrorType.user_msg}),
            {'detail': [{'msg': 'bad value', 'type': 'user_msg'}]},
        ),
        (
            (
                ('bad value',),
                {'loc': 'field', 'error_type': ErrorType.value_error},
            ),
            {
                'detail': [
                    {
                        'msg': 'bad value',
                        'loc': ['field'],
                        'type': 'value_error',
                    },
                ],
            },
        ),
        (
            (('oops',), {'error_type': 'custom_type'}),
            {'detail': [{'msg': 'oops', 'type': 'custom_type'}]},
        ),
        (
            ((RequestSerializationError('cannot parse body'),), {}),
            {
                'detail': [{'msg': 'cannot parse body', 'type': 'value_error'}],
            },
        ),
        (
            (
                (
                    ValidationError(
                        [
                            {
                                'msg': 'too short',
                                'loc': ['name'],
                                'type': 'value_error',
                            },
                        ],
                        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                    ),
                ),
                {},
            ),
            {
                'detail': [
                    {
                        'msg': 'too short',
                        'loc': ['name'],
                        'type': 'value_error',
                    },
                ],
            },
        ),
        (
            ((ResponseSchemaError('schema mismatch'),), {}),
            {
                'detail': [{'msg': 'schema mismatch', 'type': 'value_error'}],
            },
        ),
        (
            ((NotAcceptableError('unsupported media type'),), {}),
            {
                'detail': [
                    {'msg': 'unsupported media type', 'type': 'value_error'},
                ],
            },
        ),
        (
            ((NotAuthenticatedError('token expired'),), {}),
            {
                'detail': [{'msg': 'token expired', 'type': 'security'}],
            },
        ),
        (
            ((NotAuthenticatedError(),), {}),
            {
                'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
            },
        ),
    ],
)
def test_format_error_function(
    *,
    input_args: tuple[tuple[Any, ...], dict[str, Any]],
    expected: Any,
) -> None:
    """Ensures ``format_error`` works correctly."""
    assert format_error(*input_args[0], **input_args[1]) == expected


def test_format_error_from_ise_debug(
    settings: LazySettings,
) -> None:
    """Ensures ``InternalServerError`` shows details in DEBUG mode."""
    settings.DEBUG = True
    exc = InternalServerError('database is down')

    formatted = format_error(exc)

    assert formatted == {'detail': [{'msg': 'database is down'}]}


def test_format_error_from_ise_no_debug(
    settings: LazySettings,
) -> None:
    """Ensures ``InternalServerError`` hides details without DEBUG."""
    settings.DEBUG = False
    exc = InternalServerError('database is down')

    formatted = format_error(exc)

    assert formatted == {
        'detail': [{'msg': force_str(InternalServerError.default_message)}],
    }


def test_format_error_unknown_exc_raises() -> None:
    """Ensures unhandled exception types raise ``NotImplementedError``."""
    with pytest.raises(NotImplementedError, match='Cannot format error'):
        format_error(ValueError('unexpected'))
