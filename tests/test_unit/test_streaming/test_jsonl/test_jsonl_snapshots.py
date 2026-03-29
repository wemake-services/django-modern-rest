import json
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import TypeAlias

import pydantic
import pytest
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr import Headers, validate
from dmr.negotiation import ContentType
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.streaming import StreamingResponse, streaming_response_spec
from dmr.streaming.jsonl import Json, JsonLinesController
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _ClassBasedJsonL(JsonLinesController[PydanticSerializer]):
    @validate(
        streaming_response_spec(
            Json,
            content_type=ContentType.jsonl,
        ),
    )
    async def get(self) -> StreamingResponse:
        raise NotImplementedError

    async def post(self) -> AsyncIterator[Json]:
        raise NotImplementedError


def test_jsonl_default_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for default JsonL."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/jsonl', _ClassBasedJsonL.as_view())],
                ),
                config=OpenAPIConfig(
                    title='JsonL Test',
                    version='1.0',
                    openapi_version='3.2.0',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _UserEvent(pydantic.BaseModel):
    username: str


class _PaymentEvent(pydantic.BaseModel):
    amount: int


_PossibleEvents: TypeAlias = _UserEvent | _PaymentEvent


class _HeaderModel(pydantic.BaseModel):
    x_header: str = pydantic.Field(alias='X-Header')


class _ComplexJsonL(JsonLinesController[PydanticSerializer]):
    async def get(
        self,
        parsed_headers: Headers[_HeaderModel],
    ) -> AsyncIterator[_PossibleEvents]:
        return self._complex_events(parsed_headers.x_header)

    async def _complex_events(
        self,
        x_header: str,
    ) -> AsyncIterator[_PossibleEvents]:
        yield _UserEvent(username=x_header)
        yield _PaymentEvent(amount=10)


@pytest.mark.asyncio
async def test_complex_jsonl_implementation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid jsonl produces valid results."""
    request = dmr_async_rf.get('/whatever/', headers={'X-Header': 'sobolevn'})

    response = await dmr_async_rf.wrap(_ComplexJsonL.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/jsonl',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert await get_streaming_content(response) == (
        b'{"username":"sobolevn"}\n{"amount":10}\n'
    )


def test_complex_jsonl_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that complex schema is correct for jsonl."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/complex', _ComplexJsonL.as_view())],
                ),
                config=OpenAPIConfig(
                    title='Jsonl Complex Pydantic models',
                    version='1.0',
                    openapi_version='3.2.0',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
