import json
from collections.abc import Callable

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot


def _assert_on_debug(
    response: HttpResponse,
    *,
    uses_custom_error_model: bool = False,
) -> None:
    if uses_custom_error_model:
        assert json.loads(response.content) == snapshot({
            'error': [{'message': 'CSRF Failed: CSRF cookie not set.'}],
        })
    else:
        assert json.loads(response.content) == snapshot({
            'detail': [{'msg': 'CSRF Failed: CSRF cookie not set.'}],
        })


def _assert_on_non_debug(
    response: HttpResponse,
    *,
    uses_custom_error_model: bool = False,
) -> None:
    if uses_custom_error_model:
        assert json.loads(response.content) == snapshot({
            'error': [{'message': 'CSRF Failed.'}],
        })
    else:
        assert json.loads(response.content) == snapshot({
            'detail': [{'msg': 'CSRF Failed.'}],
        })


@pytest.fixture(
    params=[
        (True, _assert_on_debug),
        (False, _assert_on_non_debug),
    ],
    ids=['debug_on', 'debug_off'],
)
def assert_csrf_failure_message(
    settings: LazySettings,
    request: pytest.FixtureRequest,
) -> Callable[[HttpResponse, bool], None]:
    """Assert CSRF failure message according to debug mode setting."""
    debug_value, assert_function = request.param
    settings.DEBUG = debug_value
    return assert_function  # type: ignore[no-any-return]
