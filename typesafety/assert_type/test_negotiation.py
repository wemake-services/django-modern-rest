from typing import assert_type

from django.http import HttpRequest

from dmr.negotiation import accepts, request_parser, request_renderer
from dmr.parsers import Parser
from dmr.renderers import Renderer


def negotiated_from_request(request: HttpRequest) -> None:
    assert_type(request_parser(request), Parser | None)
    assert_type(request_parser(request, strict=True), Parser)
    assert_type(request_renderer(request), Renderer | None)
    assert_type(request_renderer(request, strict=True), Renderer)
    assert_type(
        request_renderer(request, strict=True, use_nonstreaming_renderer=True),
        Renderer,
    )
    assert_type(accepts(request, 'application/json'), bool)
