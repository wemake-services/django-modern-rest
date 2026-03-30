from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any

import pydantic
import pytest

from dmr.exceptions import DataRenderingError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import StreamingResponse
from dmr.streaming.jsonl import JsonLinesController
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _CustomModel(pydantic.BaseModel):
    username: str


class _JsonLinesEvents(JsonLinesController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[_CustomModel]:
        return self._invalid_events()

    async def _invalid_events(self) -> AsyncIterator[_CustomModel]:
        yield _CustomModel(username='1')
        yield None  # type: ignore[misc]
        yield _CustomModel(username='2')


@pytest.mark.asyncio
async def test_jsonl_event_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that we can validate event types."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_JsonLinesEvents.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == (
        b'{"username":"1"}\n'
        b'{"detail":[{"msg":"Input should be a valid dictionary '
        b'or instance of _CustomModel","loc":[],"type":"value_error"}]}\n'
        b'{"username":"2"}\n'
    )


class _CustomType:
    """Unserializable."""


class _JsonLinesCustomType(JsonLinesController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[Any]:
        return self._invalid_events()

    async def _invalid_events(self) -> AsyncIterator[Any]:
        yield _CustomType()


@pytest.mark.asyncio
async def test_jsonl_event_serialization(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that we raise on unserializable event types."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_JsonLinesCustomType.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    with pytest.raises(DataRenderingError, match='_CustomType'):
        await get_streaming_content(response)
