from __future__ import annotations

from typing import Final

from pytest_codspeed import BenchmarkFixture

from dmr import Controller
from dmr.plugins.msgspec import (
    MsgpackParser,
    MsgpackRenderer,
    MsgspecJsonParser,
    MsgspecJsonRenderer,
    MsgspecSerializer,
)
from dmr.test import DMRRequestFactory

_REPEAT: Final = 1000


class _NegotiationController(Controller[MsgspecSerializer]):
    parsers = (MsgspecJsonParser(), MsgpackParser())
    renderers = (MsgspecJsonRenderer(), MsgpackRenderer())

    def post(self) -> str:
        return 'ok'


_ENDPOINT: Final = _NegotiationController.api_endpoints['POST']


def test_request_negotiator_exact_match(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark the common exact Content-Type match."""
    request = dmr_rf.post(
        '/test',
        data=b'{}',
        content_type='application/json',
    )

    @benchmark
    def factory() -> None:
        for _ in range(_REPEAT):
            request.__dmr_parser__ = None  # type: ignore[attr-defined]
            _ENDPOINT.request_negotiator(request)


def test_response_negotiator_accept_header(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark renderer selection from a weighted Accept header."""
    request = dmr_rf.post(
        '/test',
        data=b'{}',
        content_type='application/json',
        headers={
            'Accept': 'application/msgpack;q=0.8,application/json',
        },
    )

    @benchmark
    def factory() -> None:
        for _ in range(_REPEAT):
            _ENDPOINT.response_negotiator(request)
