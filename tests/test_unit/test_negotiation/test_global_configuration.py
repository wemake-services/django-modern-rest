import json
from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any, ClassVar, final

import pydantic
import pytest
import xmltodict
from django.conf import LazySettings
from django.http import HttpResponse
from django.test import RequestFactory
from inline_snapshot import snapshot
from typing_extensions import override

from django_modern_rest import (
    Blueprint,
    Body,
    Controller,
    modify,
)
from django_modern_rest.negotiation import (
    ContentType,
    conditional_type,
    request_parser,
)
from django_modern_rest.parsers import DeserializeFunc, JsonParser, Parser, Raw
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.renderers import JsonRenderer, Renderer
from django_modern_rest.settings import Settings
from django_modern_rest.test import DMRRequestFactory


class _XMLParser(Parser):
    __slots__ = ()

    content_type: ClassVar[str] = 'application/xml'

    @override
    @classmethod
    def parse(
        cls,
        to_deserialize: Raw,
        deserializer: DeserializeFunc | None = None,
        *,
        strict: bool = True,
    ) -> Any:
        return xmltodict.parse(to_deserialize, process_namespaces=True)


class _XMLRenderer(Renderer):
    __slots__ = ()

    content_type: ClassVar[str] = 'application/xml'

    @override
    @classmethod
    def render(
        cls,
        to_serialize: Any,
        serializer: Callable[[Any], Any],
    ) -> bytes:
        raw_data = xmltodict.unparse(to_serialize, pretty=True)
        assert isinstance(raw_data, str)
        return raw_data.encode('utf8')


@pytest.fixture(autouse=True)
def _setup_parser_and_renderer(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.parsers: [_XMLParser],
        Settings.renderers: [_XMLRenderer],
    }


class _RequestModel(pydantic.BaseModel):
    root: dict[str, str]


_xml_data = """<?xml version="1.0" encoding="utf-8"?>
<root>
    <key>value</key>
</root>"""


def test_xml_parser_renderer(rf: RequestFactory) -> None:
    """Ensures we can change global parsers and renderers."""

    @final
    class _XmlController(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        def post(self) -> dict[str, str]:
            return self.parsed_body.root

    request = rf.generic(
        'POST',
        '/whatever/',
        headers={'Content-Type': 'application/xml'},
        data=_xml_data,
    )

    response = _XmlController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert response.headers == {'Content-Type': 'application/xml'}
    assert response.content == snapshot(
        b'<?xml version="1.0" encoding="utf-8"?>\n<key>value</key>',
    )


@pytest.mark.parametrize(
    ('request_headers', 'request_data', 'expected_headers', 'expected_data'),
    [
        (
            {'Content-Type': 'application/xml'},
            _xml_data,
            {'Content-Type': 'application/json'},
            b'{"key": "value"}',
        ),
        (
            {'Content-Type': 'application/xml', 'Accept': 'application/xml'},
            _xml_data,
            {'Content-Type': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<key>value</key>',
        ),
        (
            {'Content-Type': 'application/json', 'Accept': 'application/xml'},
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<key>value</key>',
        ),
        (
            {
                'Content-Type': 'application/json',
                'Accept': 'application/xml,application/json',
            },
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<key>value</key>',
        ),
        (
            {
                'Content-Type': 'application/json',
                'Accept': 'application/json,application/xml',
            },
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/json'},
            b'{"key": "value"}',
        ),
        (
            {'Content-Type': 'application/json', 'Accept': 'application/json'},
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/json'},
            b'{"key": "value"}',
        ),
        (
            {
                'Content-Type': 'application/json',
                'Accept': 'application/xml;q=0.7,application/json;q=0.9',
            },
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/json'},
            b'{"key": "value"}',
        ),
        (
            {
                'Content-Type': 'application/json',
                'Accept': 'application/xml+pretty;q=0.7,application/json;q=0.9',
            },
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/json'},
            b'{"key": "value"}',
        ),
        (
            {},
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/json'},
            b'{"key": "value"}',
        ),
        (
            {'Accept': 'application/xml,application/json'},
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<key>value</key>',
        ),
    ],
)
def test_per_controller_customization(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    request_data: Any,
    expected_headers: dict[str, str],
    expected_data: Any,
) -> None:
    """Ensures we can change per-controller parsers and renderers."""

    @final
    class _BothController(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        parsers = [JsonParser]
        renderers = [JsonRenderer]

        def post(self) -> dict[str, str]:
            parser_cls = request_parser(self.request)
            assert parser_cls
            assert parser_cls.content_type == request.content_type
            return self.parsed_body.root

    assert len(_BothController.api_endpoints['POST'].metadata.parsers) == 2
    assert len(_BothController.api_endpoints['POST'].metadata.renderers) == 2

    request = dmr_rf.generic(
        'POST',
        '/whatever/',
        headers=request_headers,
        data=request_data,
    )

    response = _BothController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == expected_headers
    assert response.content == expected_data


def test_per_blueprint_customization(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we can change per-blueprint parsers and renderers."""

    @final
    class _Blueprint(Blueprint[PydanticSerializer], Body[_RequestModel]):
        parsers = [JsonParser]
        renderers = [JsonRenderer]

        def post(self) -> dict[str, str]:
            return self.parsed_body.root

    @final
    class _BothController(Controller[PydanticSerializer]):
        blueprints = [_Blueprint]

    assert len(_BothController.api_endpoints['POST'].metadata.parsers) == 2
    assert len(_BothController.api_endpoints['POST'].metadata.renderers) == 2

    request_data = {'root': {'key': 'value'}}

    request = dmr_rf.post(
        '/whatever/',
        headers={'Content-Type': 'application/json'},
        data=json.dumps(request_data),
    )

    response = _BothController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == request_data['root']


def test_per_endpoint_customization(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we can change per-endpoint parsers and renderers."""

    @final
    class _BothController(Controller[PydanticSerializer], Body[_RequestModel]):
        @modify(parsers=[JsonParser], renderers=[JsonRenderer])
        def post(self) -> dict[str, str]:
            return self.parsed_body.root

    assert len(_BothController.api_endpoints['POST'].metadata.parsers) == 2
    assert len(_BothController.api_endpoints['POST'].metadata.renderers) == 2

    request_data = {'root': {'key': 'value'}}

    request = dmr_rf.post(
        '/whatever/',
        headers={'Content-Type': 'application/json'},
        data=json.dumps(request_data),
    )

    response = _BothController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == request_data['root']


@pytest.mark.parametrize(
    ('request_headers', 'request_data', 'expected_headers', 'expected_data'),
    [
        (
            {'Content-Type': 'application/xml', 'Accept': 'application/xml'},
            _xml_data,
            {'Content-Type': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<key>value</key>',
        ),
        (
            {'Content-Type': 'application/json', 'Accept': 'application/json'},
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/json'},
            b'"value"',
        ),
    ],
)
def test_conditional_content_type(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    request_data: Any,
    expected_headers: dict[str, str],
    expected_data: Any,
) -> None:
    """Ensures conditional content types work correctly."""

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        parsers = [JsonParser]
        renderers = [JsonRenderer]

        def post(
            self,
        ) -> Annotated[
            dict[str, str] | str,
            conditional_type({
                ContentType.json: str,
                ContentType.xml: dict[str, str],
            }),
        ]:
            if self.request.accepts(ContentType.json):
                return self.parsed_body.root['key']
            return self.parsed_body.root

    assert len(_Controller.api_endpoints['POST'].metadata.parsers) == 2
    assert len(_Controller.api_endpoints['POST'].metadata.renderers) == 2

    request = dmr_rf.generic(
        'POST',
        '/whatever/',
        headers=request_headers,
        data=request_data,
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == expected_headers
    assert response.content == expected_data


@pytest.mark.parametrize(
    ('request_headers', 'request_data', 'expected_headers'),
    [
        (
            {'Content-Type': 'application/xml', 'Accept': 'application/xml'},
            _xml_data,
            {'Content-Type': 'application/xml'},
        ),
        (
            {'Content-Type': 'application/json', 'Accept': 'application/json'},
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/json'},
        ),
    ],
)
def test_wrong_conditional_content_type(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    request_data: Any,
    expected_headers: dict[str, str],
) -> None:
    """Ensures conditional content validation works correctly."""

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        parsers = [JsonParser]
        renderers = [JsonRenderer]

        def post(
            self,
        ) -> Annotated[
            dict[str, str] | str,
            conditional_type({
                # Won't be matched:
                ContentType.json: dict[str, str],
                ContentType.xml: str,
            }),
        ]:
            # ERROR! Type to content logic is reversed:
            if self.request.accepts(ContentType.json):
                return self.parsed_body.root['key']
            return self.parsed_body.root

    assert len(_Controller.api_endpoints['POST'].metadata.parsers) == 2
    assert len(_Controller.api_endpoints['POST'].metadata.renderers) == 2

    request = dmr_rf.generic(
        'POST',
        '/whatever/',
        headers=request_headers,
        data=request_data,
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers == expected_headers, request_headers
    assert b'Input should be a valid' in response.content


def test_missing_conditional_content_type(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures conditional content might not have missing parts."""

    @final
    class _Controller(Controller[PydanticSerializer]):
        parsers = [JsonParser]
        renderers = [JsonRenderer]

        def get(
            self,
        ) -> Annotated[
            dict[str, str] | str,
            conditional_type({
                # Missing `json`:
                ContentType.xml: str,
                ContentType.form_data: dict[str, str],
            }),
        ]:
            return 'string'

    assert len(_Controller.api_endpoints['GET'].metadata.parsers) == 2
    assert len(_Controller.api_endpoints['GET'].metadata.renderers) == 2

    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'value_error',
                'loc': [],
                'msg': (
                    'Value error, Content-Type application/json '
                    'is not listed in content_types={<ContentType.xml: '
                    "'application/xml'>: <class 'str'>, "
                    "<ContentType.form_data: 'multipart/form-data'>: "
                    'dict[str, str]}'
                ),
                'input': '',
                'ctx': {
                    'error': (
                        'Content-Type application/json '
                        'is not listed in content_types={<ContentType.xml: '
                        "'application/xml'>: <class 'str'>, "
                        "<ContentType.form_data: 'multipart/form-data'>: "
                        'dict[str, str]}'
                    ),
                },
            },
        ],
    })
