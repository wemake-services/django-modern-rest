from typing import Final

from dmr import Body, Controller
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.test import DMRRequestFactory

_JSON: Final = 'application/json'


class _Controller(Controller[PydanticSerializer]):
    parsers = [JsonParser()]
    renderers = [JsonRenderer()]

    def post(self, parsed_body: Body[dict[str, str]]) -> dict[str, str]:
        raise NotImplementedError  # must not be called


def test_parser_negotiation_cache(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that memoizing does not change which parser is negotiated."""
    negotiator = _Controller.api_endpoints['POST'].request_negotiator
    headers = {'Content-Type': _JSON}

    first = negotiator(dmr_rf.get('/whatever/', headers=headers))
    second = negotiator(dmr_rf.get('/whatever/', headers=headers))

    negotiator.clear_cache()
    third = negotiator(dmr_rf.get('/whatever/', headers=headers))

    assert first.content_type == _JSON
    assert second is first
    assert third is first


def test_renderer_negotiation_cache(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that memoizing does not change which renderer is negotiated."""
    negotiator = _Controller.api_endpoints['POST'].response_negotiator
    headers = {'Accept': _JSON}

    first = negotiator(dmr_rf.get('/whatever/', headers=headers))
    second = negotiator(dmr_rf.get('/whatever/', headers=headers))

    negotiator.clear_cache()
    third = negotiator(dmr_rf.get('/whatever/', headers=headers))

    assert first.content_type == _JSON
    assert second is first
    assert third is first
