import json
from http import HTTPStatus
from typing import Any, final

import dmr.negotiation as negotiation
import pytest
from django.http import HttpRequest, HttpResponse
from typing_extensions import override

from dmr import Body, Controller
from dmr.parsers import DeserializeFunc, Parser, Raw
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer, Renderer
from dmr.test import DMRRequestFactory


class _EchoParser(Parser):
    __slots__ = ()

    content_type = 'application/*'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        return {'echo': True}


@final
class _WildcardParserController(Controller[PydanticSerializer]):
    parsers = [_EchoParser()]

    def post(self, parsed_body: Body[dict[str, bool]]) -> dict[str, bool]:
        return parsed_body


def test_wildcard_parser_cache_is_stable(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Repeated non-exact content types must keep resolving correctly."""
    for _ in range(3):
        request = dmr_rf.post(
            '/whatever/',
            headers={'Content-Type': 'application/vnd.custom+json'},
            data={},
        )

        response = _WildcardParserController.as_view()(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.CREATED
        assert json.loads(response.content) == {'echo': True}


def test_bad_content_type_is_not_cached(
    dmr_rf: DMRRequestFactory,
) -> None:
    """An unsupported ``Content-Type`` must keep failing on every call."""
    for _ in range(3):
        request = dmr_rf.post(
            '/whatever/',
            headers={'Content-Type': 'text/plain'},
            data={},
        )

        response = _WildcardParserController.as_view()(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.BAD_REQUEST


class _FakeXmlRenderer(Renderer):
    content_type = 'application/xml'

    @override
    def render(
        self,
        to_serialize: Any,
        serializer_hook: Any,
    ) -> bytes:
        return b'<xml/>'

    @property
    @override
    def validation_parser(self) -> Parser:
        return _EchoParser()


@final
class _JsonOnlyController(Controller[PydanticSerializer]):
    renderers = (JsonRenderer(),)

    def get(self) -> str:
        return 'json-only'


@final
class _JsonAndXmlController(Controller[PydanticSerializer]):
    renderers = (JsonRenderer(), _FakeXmlRenderer())

    def get(self) -> str:
        return 'json-or-xml'


def _negotiated_content_type(
    dmr_rf: DMRRequestFactory,
    controller: type[Controller[PydanticSerializer]],
    accept: str,
) -> str:
    request = dmr_rf.get('/whatever/', headers={'Accept': accept})
    response = controller.as_view()(request)
    assert isinstance(response, HttpResponse)
    return response.headers['Content-Type']


def test_fake_xml_renderer_validation_parser() -> None:
    """The XML test double must expose a working ``validation_parser``."""
    assert isinstance(_FakeXmlRenderer().validation_parser, _EchoParser)


def test_renderer_cache_not_shared(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Two endpoints with different renderers must not contaminate caches."""
    accept = 'application/xml,application/json;q=0.9'

    assert (
        _negotiated_content_type(dmr_rf, _JsonAndXmlController, accept)
        == 'application/xml'
    )
    assert (
        _negotiated_content_type(dmr_rf, _JsonOnlyController, accept)
        == 'application/json'
    )
    # Calling both again must still return the same, endpoint-specific
    # result instead of leaking a cached value from the other endpoint:
    assert (
        _negotiated_content_type(dmr_rf, _JsonAndXmlController, accept)
        == 'application/xml'
    )


def test_not_acceptable_is_not_falsely_cached(
    dmr_rf: DMRRequestFactory,
) -> None:
    """An unsupported ``Accept`` header must keep failing on every call."""
    for _ in range(3):
        request = dmr_rf.get(
            '/whatever/',
            headers={'Accept': 'application/xml'},
        )

        response = _JsonOnlyController.as_view()(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.NOT_ACCEPTABLE


def test_wildcard_parser_cache_stops_growing_past_max_size(
    dmr_rf: DMRRequestFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Once the wildcard cache is full, new content types are not stored."""
    monkeypatch.setattr(negotiation, 'MAX_CACHE_SIZE', 1)

    first = dmr_rf.post(
        '/whatever/',
        headers={'Content-Type': 'application/vnd.first+json'},
        data={},
    )
    response = _WildcardParserController.as_view()(first)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED

    # Cache is now full (maxsize=1). A second, distinct content type must
    # still resolve correctly even though it cannot be cached anymore:
    second = dmr_rf.post(
        '/whatever/',
        headers={'Content-Type': 'application/vnd.second+json'},
        data={},
    )
    response = _WildcardParserController.as_view()(second)
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == {'echo': True}


def test_renderer_cache_stops_growing_past_max_size(
    dmr_rf: DMRRequestFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Once the renderer cache is full, new ``Accept`` values still work."""
    monkeypatch.setattr(negotiation, 'MAX_CACHE_SIZE', 1)

    assert (
        _negotiated_content_type(
            dmr_rf,
            _JsonAndXmlController,
            'application/xml',
        )
        == 'application/xml'
    )
    # Cache is now full (maxsize=1). A second, distinct Accept value must
    # still resolve correctly even though it cannot be cached anymore:
    assert (
        _negotiated_content_type(
            dmr_rf,
            _JsonAndXmlController,
            'application/xml,application/json;q=0.9',
        )
        == 'application/xml'
    )
