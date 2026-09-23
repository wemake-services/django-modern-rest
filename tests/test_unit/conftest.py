import json
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeAlias

import pytest
from django.conf import LazySettings
from django.http import HttpResponse

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

CsrfFailureAssertion: TypeAlias = Callable[
    ['HttpResponse | _MonkeyPatchedWSGIResponse'],
    None,
]


@pytest.fixture(
    params=(True, False),
    ids=('debug_on', 'debug_off'),
)
def assert_csrf_failure_message(
    settings: LazySettings,
    request: pytest.FixtureRequest,
) -> CsrfFailureAssertion:
    """Assert CSRF failure message according to debug mode setting."""
    settings.DEBUG = request.param

    def factory(response: 'HttpResponse | _MonkeyPatchedWSGIResponse') -> None:
        if settings.DEBUG:
            assert json.loads(response.content) == {
                'detail': [{'msg': 'CSRF Failed: CSRF cookie not set.'}],
            }
        else:
            assert json.loads(response.content) == {
                'detail': [{'msg': 'CSRF Failed.'}],
            }

    return factory
