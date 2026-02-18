import json
from http import HTTPStatus
from typing import final

import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from django.http import HttpResponse
from django.test import RequestFactory
from inline_snapshot import snapshot

from dmr import Body, Controller, modify
from dmr.negotiation import request_parser, request_renderer
from dmr.parsers import JsonParser
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.renderers import JsonRenderer


class _RequestModel(msgspec.Struct):
    root: dict[str, str]


def test_parser_order(rf: RequestFactory) -> None:
    """Ensures we have a correct parser ordering."""
    real_request = None

    @final
    class _Controller(
        Controller[MsgspecSerializer],
        Body[_RequestModel],
    ):
        @modify(parsers=[JsonParser()], renderers=[JsonRenderer()])
        def post(self) -> dict[str, str]:
            nonlocal real_request  # noqa: WPS420
            real_request = self.request
            return self.parsed_body.root

    request = rf.generic(
        'POST',
        '/whatever/',
        headers={'Content-Type': 'application/json'},
        data=json.dumps({'root': {'a': 'b'}}),
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert real_request
    assert isinstance(request_parser(real_request), JsonParser)
    assert isinstance(request_renderer(real_request), JsonRenderer)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.content == snapshot(b'{"a": "b"}')
