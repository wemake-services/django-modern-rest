import json
from http import HTTPStatus
from typing import Any, Final, TypeAlias

import pytest
from django.conf import LazySettings
from django.http import HttpResponse, JsonResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from dmr import Body, Controller, ResponseSpec, validate
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.settings import default_parser, default_renderer
from dmr.test import DMRRequestFactory
from tests.infra.xml_format import XmlParser, XmlRenderer

_Serializes: TypeAlias = list[type[BaseSerializer]]
serializers: Final[_Serializes] = [
    PydanticSerializer,
]

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass  # noqa: WPS420
else:  # pragma: no cover
    serializers.append(MsgspecSerializer)


class _RequestModel(TypedDict):
    root: dict[str, str]


_xml_data: Final = """<?xml version="1.0" encoding="utf-8"?>
<root>
    <key>value</key>
</root>"""


@pytest.mark.parametrize('serializer', serializers)
def test_validate_negotiation(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures we can validate incorrect response content type."""

    class _XmlController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        parsers = [XmlParser(), default_parser]
        renderers = [XmlRenderer(), default_renderer]

        @validate(ResponseSpec(dict[str, str], status_code=HTTPStatus.OK))
        def post(self, parsed_body: Body[_RequestModel]) -> JsonResponse:
            return JsonResponse(parsed_body['root'], status=HTTPStatus.OK)

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/xml',
            'Accept': 'application/xml',
        },
        data=_xml_data,
    )

    response = _XmlController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        response.content
    )
    assert response.headers == {'Content-Type': 'application/xml'}
    assert response.content == snapshot(
        b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t'
        b"<msg>Negotiated renderer 'application/xml' does not match "
        b"returned content-type 'application/json'</msg>\n\t"
        b'<type>value_error</type>\n</detail>',
    )


@pytest.mark.parametrize('serializer', serializers)
def test_validate_negotiation_missing_renderer(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures we can validate incorrect response content type."""

    class _XmlController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        parsers = [XmlParser()]
        renderers = [XmlRenderer()]

        @validate(ResponseSpec(dict[str, str], status_code=HTTPStatus.OK))
        def post(self, parsed_body: Body[_RequestModel]) -> JsonResponse:
            return JsonResponse(parsed_body['root'], status=HTTPStatus.OK)

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/xml',
            'Accept': 'application/xml',
        },
        data=_xml_data,
    )

    response = _XmlController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        response.content
    )
    assert response.headers == {'Content-Type': 'application/xml'}
    assert response.content == snapshot(
        b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t'
        b"<msg>Response content type 'application/json' is not listed "
        b"as a possible to be returned ['application/xml']</msg>\n\t"
        b'<type>value_error</type>\n</detail>',
    )


@pytest.mark.parametrize('serializer', serializers)
def test_validate_negotiation_per_controller(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures we can disable content type validation."""

    class _XmlController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        validate_negotiation = False
        parsers = [XmlParser(), default_parser]
        renderers = [XmlRenderer(), default_renderer]

        @validate(ResponseSpec(dict[str, str], status_code=HTTPStatus.OK))
        def post(self, parsed_body: Body[_RequestModel]) -> JsonResponse:
            return JsonResponse(parsed_body['root'], status=HTTPStatus.OK)

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/xml',
            'Accept': 'application/xml',
        },
        data=_xml_data,
    )

    response = _XmlController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({'key': 'value'})


@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.parametrize(
    'flags',
    [{'validate_negotiation': False}, {'validate_responses': False}],
)
def test_validate_negotiation_per_endpoint(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
    flags: dict[str, Any],
) -> None:
    """Ensures we can disable content type validation."""

    class _XmlController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        parsers = [XmlParser(), default_parser]
        renderers = [XmlRenderer(), default_renderer]

        @validate(
            ResponseSpec(dict[str, str], status_code=HTTPStatus.OK),
            **flags,
        )
        def post(self, parsed_body: Body[_RequestModel]) -> JsonResponse:
            return JsonResponse(parsed_body['root'], status=HTTPStatus.OK)

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/xml',
            'Accept': 'application/xml',
        },
        data=_xml_data,
    )

    response = _XmlController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({'key': 'value'})


@pytest.mark.parametrize('serializer', serializers)
@pytest.mark.parametrize(
    'flags',
    [
        {'validate_negotiation': False},
        {'validate_responses': False},
        {'validate_negotiation': False, 'validate_responses': False},
    ],
)
def test_validate_negotiation_per_settings(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
    *,
    serializer: type[BaseSerializer],
    flags: dict[str, bool],
) -> None:
    """Ensures we can disable content type validation."""
    settings.DMR_SETTINGS = flags

    class _XmlController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        parsers = [XmlParser(), default_parser]
        renderers = [XmlRenderer(), default_renderer]

        @validate(ResponseSpec(dict[str, str], status_code=HTTPStatus.OK))
        def post(self, parsed_body: Body[_RequestModel]) -> JsonResponse:
            return JsonResponse(parsed_body['root'], status=HTTPStatus.OK)

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/xml',
            'Accept': 'application/xml',
        },
        data=_xml_data,
    )

    response = _XmlController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({'key': 'value'})


@pytest.mark.parametrize('serializer', serializers)
def test_validate_negotiation_missing_type(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures we returning content type that is not support raises."""

    class _XmlController(
        Controller[serializer],  # type: ignore[valid-type]
    ):
        parsers = [XmlParser()]
        renderers = [XmlRenderer()]

        @validate(
            ResponseSpec(dict[str, str], status_code=HTTPStatus.OK),
            validate_negotiation=False,
        )
        def post(self, parsed_body: Body[_RequestModel]) -> JsonResponse:
            return JsonResponse(parsed_body['root'], status=HTTPStatus.OK)

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/xml',
            'Accept': 'application/xml',
        },
        data=_xml_data,
    )

    response = _XmlController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        response.content
    )
    assert response.headers == {'Content-Type': 'application/xml'}
    assert response.content == snapshot(
        b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t'
        b"<msg>Response content type 'application/json' is not listed "
        b"as a possible to be returned ['application/xml']</msg>\n\t"
        b'<type>value_error</type>\n</detail>',
    )
