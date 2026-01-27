import json
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse
from django.test import RequestFactory
from inline_snapshot import snapshot

from django_modern_rest import Body, Controller, modify
from django_modern_rest.negotiation import request_parser, request_renderer
from django_modern_rest.parsers import JsonParser
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.renderers import JsonRenderer


class _RequestModel(pydantic.BaseModel):
    root: dict[str, str]


def test_parser_order(rf: RequestFactory) -> None:
    """Ensures we have a correct parser ordering."""
    real_request = None

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        @modify(parsers=[JsonParser], renderers=[JsonRenderer])
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
    assert request_parser(real_request) is JsonParser
    assert request_renderer(real_request) is JsonRenderer
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.content == snapshot(b'{"a": "b"}')
