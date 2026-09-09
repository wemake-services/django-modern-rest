import json
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeAlias

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot

CsrfFailureAssertion: TypeAlias = Callable[[HttpResponse], None]


@pytest.fixture(
    params=[(True), (False)],
    ids=['debug_on', 'debug_off'],
)
def assert_csrf_failure_message(
    settings: LazySettings,
    request: pytest.FixtureRequest,
) -> 'CsrfFailureAssertion':
    """Assert CSRF failure message according to debug mode setting."""
    is_debug_mode_active = request.param
    settings.DEBUG = is_debug_mode_active

    def _assert(response: HttpResponse) -> None:
        if is_debug_mode_active:
            assert json.loads(response.content) == snapshot({
                'detail': [{'msg': 'CSRF Failed: CSRF cookie not set.'}],
            })
        else:
            assert json.loads(response.content) == snapshot({
                'detail': [{'msg': 'CSRF Failed.'}],
            })

    return _assert
