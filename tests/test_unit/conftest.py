import json
from collections.abc import Callable
from typing import TypeAlias

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot

CsrfFailureAssertion: TypeAlias = Callable[[HttpResponse], None]


def assert_csrf_failure_message(
    settings: LazySettings,
) -> CsrfFailureAssertion:
    """Assert CSRF failure message according to debug mode setting."""

    def factory(response: HttpResponse) -> None:
        if settings.DEBUG:
            assert json.loads(response.content) == snapshot({
                'detail': [{'msg': 'CSRF Failed: CSRF cookie not set.'}],
            })
        else:
            assert json.loads(response.content) == snapshot({
                'detail': [{'msg': 'CSRF Failed.'}],
            })

    return _assert
