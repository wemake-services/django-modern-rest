from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from django.http import HttpRequest

from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSEContext,
    SSEData,
    SSEResponse,
    SSEStreamingResponse,
    SSEvent,
    sse,
)
from dmr.test import DMRAsyncRequestFactory

if TYPE_CHECKING:
    from tests.test_sse.conftest import (  # pyright: ignore[reportMissingImports]
        GetStreamingContent,
    )


def _positive_numbers(
    event: Any,
    model: Any,
    serializer: type['BaseSerializer'],
) -> SSEData:
    if (
        isinstance(event, SSEvent)
        and isinstance(event.data, int)
        and event.data < 0
    ):
        raise ValueError(f'Negative number found: {event.data}')
    return event  # type: ignore[no-any-return]


class _PositiveStreamingResponse(SSEStreamingResponse):
    validation_pipeline = (
        *SSEStreamingResponse.validation_pipeline,
        _positive_numbers,
    )


async def _valid_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    yield SSEvent(1)
    yield SSEvent(-1)


@sse(
    PydanticSerializer,
    sse_streaming_response_cls=_PositiveStreamingResponse,
)
async def _valid_sse(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(_valid_events(PydanticSerializer, renderer))


@pytest.mark.asyncio
async def test_sse_extra_validation_response(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_valid_sse.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(ValueError, match='Negative number found: -1'):
        await get_streaming_content(response)
