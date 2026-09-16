from __future__ import annotations

from typing import Final

from pytest_codspeed import BenchmarkFixture

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.renderers import Renderer
from dmr.test import DMRRequestFactory

#: What almost every API client sends.
_API_CLIENT_ACCEPT: Final = 'application/json'

#: What a browser sends, it has to go through the full negotiation.
_BROWSER_ACCEPT: Final = (
    'text/html,application/xhtml+xml,application/xml;q=0.9,'
    'image/avif,image/webp,image/apng,*/*;q=0.8,'
    'application/signed-exchange;v=b3;q=0.7'
)


class _NegotiatedController(Controller[MsgspecSerializer]):
    def get(self) -> int:
        return 1


def test_response_negotiation_api_client(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark the `Accept` header that hits the exact match."""
    negotiator = _NegotiatedController.api_endpoints['GET'].response_negotiator
    request = dmr_rf.get('/test', headers={'Accept': _API_CLIENT_ACCEPT})

    def factory() -> Renderer:
        return negotiator(request)

    assert benchmark(factory).content_type == _API_CLIENT_ACCEPT


def test_response_negotiation_browser(
    benchmark: BenchmarkFixture,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Benchmark the `Accept` header that needs the full negotiation."""
    negotiator = _NegotiatedController.api_endpoints['GET'].response_negotiator
    request = dmr_rf.get('/test', headers={'Accept': _BROWSER_ACCEPT})

    def factory() -> Renderer:
        return negotiator(request)

    assert benchmark(factory).content_type == _API_CLIENT_ACCEPT
