from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any, Final

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse

from dmr import Body
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.settings import Settings, default_parser, default_renderer
from dmr.streaming.sse import SSEController, SSEvent
from dmr.streaming.sse.renderer import SSERenderer
from dmr.streaming.sse.validation import SSEStreamingValidator
from dmr.test import DMRAsyncRequestFactory
from tests.infra.xml_format import XmlParser, XmlRenderer


def test_single_streaming_renderer(
    settings: LazySettings,
) -> None:
    """Ensure that streaming renderer can't be the only one."""
    settings.DMR_SETTINGS = {
        Settings.renderers: [
            SSERenderer(
                PydanticSerializer,
                JsonRenderer(),
                SSEStreamingValidator,
            ),
        ],
    }

    with pytest.raises(
        EndpointMetadataError,
        match='At least one non-stream renderer is required',
    ):

        class _ClassBasedSSE(SSEController[PydanticSerializer]):
            async def get(self) -> AsyncIterator[Any]:
                raise NotImplementedError


_xml_wrong_data: Final = """<?xml version="1.0" encoding="utf-8"?>
<user_id>abc</user_id>"""


class _BodyModel(pydantic.BaseModel):
    user_id: int


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        'request_headers',
        'request_data',
        'expected_content_type',
        'expected_content',
    ),
    [
        (
            {'Accept': 'application/xml', 'Content-Type': 'application/xml'},
            _xml_wrong_data,
            'application/xml',
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t'
                b'<msg>Input should be a valid integer, '
                b'unable to parse string as an integer</msg>\n\t\n\t'
                b'<loc>parsed_body</loc>\n\t<loc>user_id</loc>\n\t'
                b'<type>value_error</type>\n</detail>'
            ),
        ),
        (
            {'Accept': 'application/xml', 'Content-Type': 'application/json'},
            b'{"user_id": "abc"}',
            'application/xml',
            (
                b'<?xml version="1.0" encoding="utf-8"?>\n<detail>\n\t'
                b'<msg>Input should be a valid integer, '
                b'unable to parse string as an integer</msg>\n\t\n\t'
                b'<loc>parsed_body</loc>\n\t<loc>user_id</loc>\n\t'
                b'<type>value_error</type>\n</detail>'
            ),
        ),
        (
            {'Accept': 'application/json', 'Content-Type': 'application/xml'},
            _xml_wrong_data,
            'application/json',
            (
                b'{"detail":[{"msg":"Input should be a valid integer, '
                b'unable to parse string as an integer",'
                b'"loc":["parsed_body","user_id"],"type":"value_error"}]}'
            ),
        ),
    ],
)
async def test_sse_negotiation(
    settings: LazySettings,
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    request_headers: dict[str, str],
    request_data: bytes,
    expected_content_type: str,
    expected_content: bytes,
) -> None:
    """Ensures that content negotiation work for error messages."""
    settings.DMR_SETTINGS = {
        Settings.renderers: [XmlRenderer(), default_renderer],
        Settings.parsers: [XmlParser(), default_parser],
    }

    class _ClassBasedSSE(SSEController[PydanticSerializer]):
        async def post(
            self,
            parsed_body: Body[_BodyModel],
        ) -> AsyncIterator[SSEvent[int]]:
            raise NotImplementedError

    request = dmr_async_rf.post(
        '/whatever/',
        data=request_data,
        headers=request_headers,
    )

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': expected_content_type}
    assert response.content == expected_content
