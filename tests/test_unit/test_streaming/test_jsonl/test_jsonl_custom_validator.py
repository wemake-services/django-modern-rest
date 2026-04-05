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
from dmr.streaming.jsonl import JsonLinesController
from dmr.streaming.jsonl.validation import (
    JsonLinesPipeline,
    JsonLinesStreamingValidator,
)
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _PositiveStreamingValidator(JsonLinesStreamingValidator):
    @override
    def validation_pipeline(self) -> Iterable[JsonLinesPipeline]:
        return (
            *super().validation_pipeline(),
            self._positive_numbers,
        )

    def _positive_numbers(
        self,
        event: Any,
        model: Any,
        serializer: type[BaseSerializer],
    ) -> Any:
        if isinstance(event, int) and event < 0:
            raise ValidationError([
                ErrorDetail(
                    msg=f'Negative number found: {event}',
                    type=ErrorType.streaming,
                ),
            ])
        return event


class _JsonLinesEvents(JsonLinesController[PydanticSerializer]):
    streaming_validator_cls = _PositiveStreamingValidator

    async def get(self) -> AsyncIterator[int]:
        return self._valid_events()

    async def _valid_events(self) -> AsyncIterator[int]:
        yield 1
        yield -1


@pytest.mark.asyncio
async def test_jsonl_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that validation errors render correctly."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_JsonLinesEvents.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'1\n'
        b'{"detail":[{"msg":"Negative number found: -1","type":"streaming"}]}\n'
    )


class _UnhandledValidator(JsonLinesStreamingValidator):
    @override
    def validation_pipeline(self) -> Iterable[JsonLinesPipeline]:
        return (
            *super().validation_pipeline(),
            self._positive_numbers,
        )

    def _positive_numbers(
        self,
        event: Any,
        model: Any,
        serializer: type[BaseSerializer],
    ) -> Any:
        if isinstance(event, int) and event < 0:
            raise ValueError(f'Negative number found: {event}')
        return event


class _UnhandledError(JsonLinesController[PydanticSerializer]):
    streaming_validator_cls = _UnhandledValidator

    async def get(self) -> AsyncIterator[int]:
        return self._valid_events()

    async def _valid_events(self) -> AsyncIterator[int]:
        yield 1
        yield -1


@pytest.mark.asyncio
async def test_jsonl_validation_bubbles_unhandled(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that validation errors bubble up when not handled."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_UnhandledError.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(ValueError, match='Negative'):
        await get_streaming_content(response)
