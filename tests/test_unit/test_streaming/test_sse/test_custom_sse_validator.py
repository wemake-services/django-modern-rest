from collections.abc import AsyncIterator, Iterable
from http import HTTPStatus
from typing import Any

import pytest
from typing_extensions import override

from dmr.errors import ErrorDetail, ErrorType
from dmr.exceptions import ValidationError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.streaming import StreamingResponse
from dmr.streaming.sse import SSE, SSEController, SSEvent
from dmr.streaming.sse.validation import SSEPipeline, SSEStreamingValidator
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _PositiveStreamingValidator(SSEStreamingValidator):
    @override
    def validation_pipeline(self) -> Iterable[SSEPipeline]:
        return (
            *super().validation_pipeline(),
            self._positive_numbers,
        )

    def _positive_numbers(
        self,
        event: SSE,
        model: Any,
        serializer: type[BaseSerializer],
    ) -> SSE:
        if isinstance(event.data, int) and event.data < 0:
            raise ValidationError([
                ErrorDetail(
                    msg=f'Negative number found: {event.data}',
                    type=ErrorType.streaming,
                ),
            ])
        return event


class _ClassBasedSSE(SSEController[PydanticSerializer]):
    streaming_validator_cls = _PositiveStreamingValidator

    async def get(self) -> AsyncIterator[SSEvent[int]]:
        return self._valid_events()

    async def _valid_events(self) -> AsyncIterator[SSEvent[int]]:
        yield SSEvent(1)
        yield SSEvent(-1)


@pytest.mark.asyncio
async def test_sse_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that validation errors render correctly."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_ClassBasedSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'data: 1\r\n'
        b'\r\n'
        b'event: error\r\n'
        b'data: {"detail":[{"msg":"Negative number found: -1",'
        b'"type":"streaming"}]}\r\n'
        b'\r\n'
    )


class _UnhandledValidator(SSEStreamingValidator):
    @override
    def validation_pipeline(self) -> Iterable[SSEPipeline]:
        return (
            *super().validation_pipeline(),
            self._positive_numbers,
        )

    def _positive_numbers(
        self,
        event: SSE,
        model: Any,
        serializer: type[BaseSerializer],
    ) -> SSE:
        if isinstance(event.data, int) and event.data < 0:
            raise ValueError(f'Negative number found: {event.data}')
        return event


class _UnhandledSSE(SSEController[PydanticSerializer]):
    streaming_validator_cls = _UnhandledValidator

    async def get(self) -> AsyncIterator[SSEvent[int]]:
        return self._valid_events()

    async def _valid_events(self) -> AsyncIterator[SSEvent[int]]:
        yield SSEvent(1)
        yield SSEvent(-1)


@pytest.mark.asyncio
async def test_sse_validation_bubbles_unhandled(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that validation errors bubble up when not handled."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_UnhandledSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(ValueError, match='Negative'):
        await get_streaming_content(response)
