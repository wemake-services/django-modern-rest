import sys
from typing import Final

import pytest

from dmr import Body, Controller
from dmr.exceptions import NotAcceptableError, RequestSerializationError
from dmr.negotiation import RequestNegotiator, ResponseNegotiator
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.test import DMRRequestFactory

_JSON: Final = 'application/json'
_XML: Final = 'application/xml'
_ANY_APPLICATION: Final = 'application/*'
_IMAGE: Final = 'image/png'


class _MultiTypeController(Controller[PydanticSerializer]):
    parsers = [JsonParser(), JsonParser(_ANY_APPLICATION)]
    renderers = [JsonRenderer(), JsonRenderer(_XML)]

    def post(self, parsed_body: Body[dict[str, str]]) -> dict[str, str]:
        raise NotImplementedError  # must not be called


class _JsonOnlyController(Controller[PydanticSerializer]):
    parsers = [JsonParser()]
    renderers = [JsonRenderer()]

    def post(self, parsed_body: Body[dict[str, str]]) -> dict[str, str]:
        raise NotImplementedError  # must not be called


@pytest.fixture
def request_negotiator() -> RequestNegotiator:
    """Return a request negotiator that has not memoized anything yet."""
    negotiator = _MultiTypeController.api_endpoints['POST'].request_negotiator
    negotiator.clear_cache()
    return negotiator


@pytest.fixture
def response_negotiator() -> ResponseNegotiator:
    """Return a response negotiator that has not memoized anything yet."""
    negotiator = _MultiTypeController.api_endpoints['POST'].response_negotiator
    negotiator.clear_cache()
    return negotiator


def _cache_stats(
    negotiator: RequestNegotiator | ResponseNegotiator,
) -> tuple[int, int]:
    """Return how many times the negotiation was and was not memoized."""
    cache_info = negotiator._negotiate.cache_info()
    return cache_info.hits, cache_info.misses


def test_parser_negotiation_is_cached(
    dmr_rf: DMRRequestFactory,
    request_negotiator: RequestNegotiator,
) -> None:
    """Ensures that the same `Content-Type` is only negotiated once."""
    exact = request_negotiator(
        dmr_rf.get('/whatever/', headers={'Content-Type': _JSON}),
    )
    fuzzy = request_negotiator(
        dmr_rf.get('/whatever/', headers={'Content-Type': _XML}),
    )

    assert exact.content_type == _JSON
    assert fuzzy.content_type == _ANY_APPLICATION
    assert _cache_stats(request_negotiator) == (0, 2)

    # The very same headers must not be negotiated for the second time,
    # while still resolving to exactly the same parsers:
    assert (
        request_negotiator(
            dmr_rf.get('/whatever/', headers={'Content-Type': _JSON}),
        )
        is exact
    )
    assert (
        request_negotiator(
            dmr_rf.get('/whatever/', headers={'Content-Type': _XML}),
        )
        is fuzzy
    )
    assert _cache_stats(request_negotiator) == (2, 2)


def test_unsupported_content_type_is_cached(
    dmr_rf: DMRRequestFactory,
    request_negotiator: RequestNegotiator,
) -> None:
    """Ensures that unsupported `Content-Type` headers are memoized too.

    Only the decision is memoized, the error is still raised
    for every single request that carries this header.
    """
    for _ in range(2):
        with pytest.raises(RequestSerializationError, match=_IMAGE):
            request_negotiator(
                dmr_rf.get('/whatever/', headers={'Content-Type': _IMAGE}),
            )

    assert _cache_stats(request_negotiator) == (1, 1)


def test_renderer_negotiation_is_cached(
    dmr_rf: DMRRequestFactory,
    response_negotiator: ResponseNegotiator,
) -> None:
    """Ensures that the same `Accept` header is only negotiated once."""
    json_renderer = response_negotiator(
        dmr_rf.get('/whatever/', headers={'Accept': _JSON}),
    )
    xml_renderer = response_negotiator(
        dmr_rf.get('/whatever/', headers={'Accept': _XML}),
    )

    assert json_renderer.content_type == _JSON
    assert xml_renderer.content_type == _XML
    assert _cache_stats(response_negotiator) == (0, 2)

    # The very same headers must not be negotiated for the second time,
    # while still resolving to exactly the same renderers:
    assert (
        response_negotiator(dmr_rf.get('/whatever/', headers={'Accept': _JSON}))
        is json_renderer
    )
    assert (
        response_negotiator(dmr_rf.get('/whatever/', headers={'Accept': _XML}))
        is xml_renderer
    )
    assert _cache_stats(response_negotiator) == (2, 2)


def test_unsupported_accept_is_cached(
    dmr_rf: DMRRequestFactory,
    response_negotiator: ResponseNegotiator,
) -> None:
    """Ensures that unsupported `Accept` headers are memoized too.

    Only the decision is memoized, the error is still raised
    for every single request that carries this header.
    """
    for _ in range(2):
        with pytest.raises(NotAcceptableError, match=_IMAGE):
            response_negotiator(
                dmr_rf.get('/whatever/', headers={'Accept': _IMAGE}),
            )

    assert _cache_stats(response_negotiator) == (1, 1)


def test_caches_are_not_shared_between_endpoints(
    dmr_rf: DMRRequestFactory,
    response_negotiator: ResponseNegotiator,
) -> None:
    """Ensures that every endpoint memoizes its own renderers."""
    json_only = _JsonOnlyController.api_endpoints['POST'].response_negotiator

    renderer = response_negotiator(
        dmr_rf.get('/whatever/', headers={'Accept': _XML}),
    )

    assert renderer.content_type == _XML
    # The very same header is not acceptable for the other endpoint,
    # even though it is already memoized as `application/xml` here:
    with pytest.raises(NotAcceptableError, match=_XML):
        json_only(dmr_rf.get('/whatever/', headers={'Accept': _XML}))


def test_clear_cache(
    dmr_rf: DMRRequestFactory,
    request_negotiator: RequestNegotiator,
    response_negotiator: ResponseNegotiator,
) -> None:
    """Ensures that negotiators can be told to forget what they decided."""
    request_negotiator(
        dmr_rf.get('/whatever/', headers={'Content-Type': _JSON}),
    )
    response_negotiator(dmr_rf.get('/whatever/', headers={'Accept': _JSON}))

    assert _cache_stats(request_negotiator) == (0, 1)
    assert _cache_stats(response_negotiator) == (0, 1)

    request_negotiator.clear_cache()
    response_negotiator.clear_cache()

    assert _cache_stats(request_negotiator) == (0, 0)
    assert _cache_stats(response_negotiator) == (0, 0)


@pytest.mark.skipif(
    not hasattr(sys, 'getrefcount'),
    reason='Only refcounted implementations can leak this way, PyPy cannot',
)
def test_negotiators_are_not_self_referencing() -> None:
    """Ensures that memoization does not leak the negotiators themselves.

    Caching a bound method stores ``self`` inside the cache that ``self``
    owns. That is a reference cycle: the negotiator would only ever be
    freed by the ``gc``, never by its own refcount dropping to zero.
    """
    metadata = _JsonOnlyController.api_endpoints['POST'].metadata

    request_negotiator = RequestNegotiator(metadata, PydanticSerializer)
    response_negotiator = ResponseNegotiator(
        metadata,
        PydanticSerializer,
        streaming=False,
    )

    # How many references a local variable alone is worth
    # is up to the interpreter, so we compare with an object
    # that is only referenced by its own local variable:
    baseline = object()

    assert sys.getrefcount(request_negotiator) == sys.getrefcount(baseline)
    assert sys.getrefcount(response_negotiator) == sys.getrefcount(baseline)
