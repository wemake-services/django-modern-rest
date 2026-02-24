import json
from http import HTTPMethod, HTTPStatus
from typing import Annotated, Any, final

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from django.test import RequestFactory
from inline_snapshot import snapshot
from typing_extensions import TypedDict, override

from dmr import (
    Blueprint,
    Body,
    Controller,
    ResponseSpec,
    modify,
    validate,
)
from dmr.errors import ErrorType
from dmr.negotiation import (
    ContentType,
    conditional_type,
    request_parser,
)
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory
from tests.infra.xml_format import XmlParser, XmlRenderer


@pytest.fixture(autouse=True)
def _setup_parser_and_renderer(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.parsers: [XmlParser()],
        Settings.renderers: [XmlRenderer()],
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
            {'Content-Type': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<key>value</key>',
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
            {'Content-Type': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<key>value</key>',
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
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]

        def post(self) -> dict[str, str]:
            parser = request_parser(self.request)
            assert parser
            assert parser.content_type == request.content_type
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
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]

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
    assert response.headers == {'Content-Type': 'application/xml'}
    assert b'<key>value</key>' in response.content


def test_per_endpoint_customization(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we can change per-endpoint parsers and renderers."""

    @final
    class _BothController(Controller[PydanticSerializer], Body[_RequestModel]):
        @modify(
            parsers=[XmlParser(), JsonParser()],
            renderers=[XmlRenderer(), JsonRenderer()],
        )
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
    assert response.headers == {'Content-Type': 'application/xml'}
    assert b'<key>value</key>' in response.content


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
@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
def test_conditional_content_type(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    request_data: Any,
    expected_headers: dict[str, str],
    expected_data: Any,
    method: HTTPMethod,
) -> None:
    """Ensures conditional content types work correctly."""

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]

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

        @validate(
            ResponseSpec(
                return_type=Annotated[
                    dict[str, str] | str,
                    conditional_type({
                        ContentType.json: str,
                        ContentType.xml: dict[str, str],
                    }),
                ],
                status_code=HTTPStatus.CREATED,
            ),
        )
        def put(self) -> HttpResponse:
            if self.request.accepts(ContentType.json):
                return self.to_response(
                    self.parsed_body.root['key'],
                    status_code=HTTPStatus.CREATED,
                )
            return self.to_response(
                self.parsed_body.root,
                status_code=HTTPStatus.CREATED,
            )

    assert len(_Controller.api_endpoints[str(method)].metadata.parsers) == 2
    assert len(_Controller.api_endpoints[str(method)].metadata.renderers) == 2

    request = dmr_rf.generic(
        str(method),
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
@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
    ],
)
def test_wrong_conditional_content_type(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    request_data: Any,
    expected_headers: dict[str, str],
    method: HTTPMethod,
) -> None:
    """Ensures conditional content validation works correctly."""

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]

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

        @validate(
            ResponseSpec(
                return_type=Annotated[
                    dict[str, str] | str,
                    conditional_type({
                        # Won't be matched:
                        ContentType.json: dict[str, str],
                        ContentType.xml: str,
                    }),
                ],
                status_code=HTTPStatus.CREATED,
            ),
        )
        def put(self) -> HttpResponse:
            # ERROR! Type to content logic is reversed:
            if self.request.accepts(ContentType.json):
                return self.to_response(
                    self.parsed_body.root['key'],
                    status_code=HTTPStatus.CREATED,
                )
            return self.to_response(
                self.parsed_body.root,
                status_code=HTTPStatus.CREATED,
            )

    assert len(_Controller.api_endpoints[str(method)].metadata.parsers) == 2
    assert len(_Controller.api_endpoints[str(method)].metadata.renderers) == 2

    request = dmr_rf.generic(
        str(method),
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
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]

        def get(
            self,
        ) -> Annotated[
            dict[str, str] | str,
            conditional_type({
                # Missing `json`:
                ContentType.xml: str,
                ContentType.multipart_form_data: dict[str, str],
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
                'msg': (
                    "Content-Type 'application/json' is not listed "
                    "in supported content types ['application/xml', "
                    "'multipart/form-data']"
                ),
                'type': 'value_error',
            },
        ],
    })


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
            b'"value"',
            {'Content-Type': 'application/json'},
            b'{"key": "value"}',
        ),
    ],
)
def test_conditional_body_model(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    request_data: Any,
    expected_headers: dict[str, str],
    expected_data: Any,
) -> None:
    """Ensures conditional body models work correctly."""

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[
            Annotated[
                _RequestModel | str,
                conditional_type({
                    ContentType.json: str,
                    ContentType.xml: _RequestModel,
                }),
            ]
        ],
    ):
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]

        def post(self) -> dict[str, str]:
            if isinstance(self.parsed_body, _RequestModel):
                return self.parsed_body.root
            return {'key': self.parsed_body}

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
        # xml data with json structure:
        (
            {'Content-Type': 'application/xml', 'Accept': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<item>String</item>',
            {'Content-Type': 'application/xml'},
        ),
        # json data with xml structure:
        (
            {'Content-Type': 'application/json', 'Accept': 'application/json'},
            b'{"root": {"key": "value"}}',
            {'Content-Type': 'application/json'},
        ),
        # Mixed up data and content types:
        (
            {'Content-Type': 'application/xml'},
            b'{"key": "value"}',
            {'Content-Type': 'application/xml'},
        ),
        (
            {'Content-Type': 'application/json'},
            _xml_data,
            {'Content-Type': 'application/xml'},
        ),
        # Just wrong json data:
        (
            {'Content-Type': 'application/json', 'Accept': 'application/json'},
            b'1',
            {'Content-Type': 'application/json'},
        ),
        (
            {'Content-Type': 'application/json', 'Accept': 'application/json'},
            b'[]',
            {'Content-Type': 'application/json'},
        ),
        # Just wrong xml data:
        (
            {'Content-Type': 'application/xml', 'Accept': 'application/xml'},
            b'<?xml version="1.0" encoding="utf-8"?>\n<item>1</item>',
            {'Content-Type': 'application/xml'},
        ),
    ],
)
def test_conditional_body_model_wrong(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    request_data: Any,
    expected_headers: dict[str, str],
) -> None:
    """Ensures conditional body models validates correctly."""

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[
            Annotated[
                _RequestModel | dict[str, str],
                conditional_type({
                    ContentType.json: dict[str, str],
                    ContentType.xml: _RequestModel,
                }),
            ]
        ],
    ):
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]

        def post(self) -> dict[str, str]:
            raise NotImplementedError

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
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == expected_headers


@final
class _CustomErrorMsg(TypedDict):
    reason: str


@final
class _CustomJsonErrorModel(TypedDict):
    json_errors: list[_CustomErrorMsg]


@final
class _CustomXmlErrorModel(TypedDict):
    xml_errors: dict[str, str]


@pytest.mark.parametrize(
    ('request_headers', 'expected_headers', 'expected_data'),
    [
        (
            {'Content-Type': 'application/xml', 'Accept': 'application/xml'},
            {'Content-Type': 'application/xml'},
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n'
                b'<xml_errors>\n\t'
                b'<parsed_body.root>Field required</parsed_body.root>\n'
                b'</xml_errors>'
            ),
        ),
        (
            {'Content-Type': 'application/json', 'Accept': 'application/json'},
            {'Content-Type': 'application/json'},
            (
                b'{"json_errors": [{"reason": '
                b'"Input should be a valid dictionary or instance '
                b"of _RequestModel: ['parsed_body']\"}]}"
            ),
        ),
    ],
)
def test_conditional_error_model(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    expected_headers: dict[str, str],
    expected_data: Any,
) -> None:
    """Ensures conditional errors with content types work correctly."""

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]
        error_model = Annotated[
            _CustomJsonErrorModel | _CustomXmlErrorModel,
            conditional_type({
                ContentType.json: _CustomJsonErrorModel,
                ContentType.xml: _CustomXmlErrorModel,
            }),
        ]

        def post(self) -> str:
            raise NotImplementedError

        @override
        def format_error(
            self,
            error: str | Exception,
            *,
            loc: str | None = None,
            error_type: str | ErrorType | None = None,
        ) -> _CustomJsonErrorModel | _CustomXmlErrorModel:
            original = super().format_error(
                error,
                loc=loc,
                error_type=error_type,
            )
            if self.request.accepts(ContentType.json):
                return {
                    'json_errors': [
                        {'reason': f'{detail["msg"]}: {detail["loc"]}'}
                        for detail in original['detail']
                    ],
                }
            return {
                'xml_errors': {
                    '.'.join(detail['loc']): detail['msg']
                    for detail in original['detail']
                },
            }

    request = dmr_rf.post(
        '/whatever/',
        headers=request_headers,
        data='',
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == expected_headers
    assert response.content == expected_data


@pytest.mark.parametrize(
    ('request_headers', 'expected_headers', 'expected_data'),
    [
        (
            {'Content-Type': 'application/xml', 'Accept': 'application/xml'},
            {'Content-Type': 'application/xml'},
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n<json_errors>\n\t'
                b'<reason>Field required: '
                b"['xml_errors']</reason>\n</json_errors>"
            ),
        ),
        (
            {'Content-Type': 'application/json', 'Accept': 'application/json'},
            {'Content-Type': 'application/json'},
            b'{"xml_errors": {"json_errors": "Field required"}}',
        ),
    ],
)
def test_conditional_error_model_wrong(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
    expected_headers: dict[str, str],
    expected_data: Any,
) -> None:
    """Ensures conditional errors are validated."""

    @final
    class _Controller(
        Controller[PydanticSerializer],
        Body[_RequestModel],
    ):
        parsers = [XmlParser(), JsonParser()]
        renderers = [XmlRenderer(), JsonRenderer()]
        error_model = Annotated[
            _CustomJsonErrorModel | _CustomXmlErrorModel,
            conditional_type({
                ContentType.json: _CustomJsonErrorModel,
                ContentType.xml: _CustomXmlErrorModel,
            }),
        ]

        def post(self) -> str:
            raise NotImplementedError

        @override
        def format_error(
            self,
            error: str | Exception,
            *,
            loc: str | None = None,
            error_type: str | ErrorType | None = None,
        ) -> _CustomJsonErrorModel | _CustomXmlErrorModel:
            original = super().format_error(
                error,
                loc=loc,
                error_type=error_type,
            )
            # NOTE: we change the formats to trigger the validation:
            if self.request.accepts(ContentType.xml):
                return {
                    'json_errors': [
                        {'reason': f'{detail["msg"]}: {detail["loc"]}'}
                        for detail in original['detail']
                    ],
                }
            return {
                'xml_errors': {
                    '.'.join(detail['loc']): detail['msg']
                    for detail in original['detail']
                },
            }

    request = dmr_rf.post(
        '/whatever/',
        headers=request_headers,
        data='',
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers == expected_headers
    assert response.content == expected_data
