import dataclasses
import json
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Final, TypeAlias

import pydantic
import pytest
from django.http import HttpRequest, HttpResponse
from typing_extensions import TypedDict

from dmr.components import Cookies, Headers, Path, Query
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSEContext,
    SSEData,
    SSEResponse,
    SSEStreamingResponse,
    sse,
)
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content

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


async def _empty_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    # # This is needed to make `_empty_events` an async iterator:
    if False:  # noqa: WPS314
        yield b''  # type: ignore[unreachable]


class _PathModel(TypedDict):
    user_id: int
    stream_name: str


@dataclasses.dataclass
class _QueryModel:
    filter: str


class _HeaderModel(pydantic.BaseModel):
    whatever: str


@pytest.mark.asyncio
async def test_sse_parses_all_components(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that sse can parse all components."""

    @sse(
        PydanticSerializer,
        path=Path[_PathModel],
        query=Query[_QueryModel],
        headers=Headers[_HeaderModel],
        cookies=Cookies[dict[str, str]],
    )
    async def _sse_components(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext[
            _PathModel,
            _QueryModel,
            _HeaderModel,
            dict[str, str],
        ],
    ) -> SSEResponse:
        assert context.parsed_path == {'user_id': 1, 'stream_name': 'abc'}
        assert context.parsed_query == _QueryModel(filter='python')
        assert context.parsed_headers == _HeaderModel(whatever='yes')
        assert context.parsed_cookies == {'session_id': 'unique'}
        return SSEResponse(_empty_events(PydanticSerializer, renderer))

    request = dmr_async_rf.get(
        '/whatever/?filter=python',
        headers={
            'whatever': 'yes',
        },
    )
    request.COOKIES = {
        'session_id': 'unique',
    }

    response = await dmr_async_rf.wrap(
        _sse_components.as_view()(request, user_id=1, stream_name='abc'),
    )

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == b''


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_sse_parsing_error(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that sse can parse all components."""

    @sse(
        serializer,
        path=Path[_PathModel],
    )
    async def _sse_components(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext[_PathModel],
    ) -> SSEResponse:
        raise NotImplementedError

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _sse_components.as_view()(request, user_id='abc'),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    response_content = json.loads(response.content)
    # Different serializers have different errors:
    assert response_content.keys() == {'detail'}
    assert response_content['detail']
    assert response_content['detail'][0]['type'] == 'value_error'
