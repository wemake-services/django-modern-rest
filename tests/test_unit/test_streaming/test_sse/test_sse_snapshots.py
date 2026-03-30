import json
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Literal, TypeAlias

import pydantic
import pytest
from django.urls import path
from pydantic.json_schema import JsonSchemaValue, SkipJsonSchema
from pydantic_core import core_schema as cs
from syrupy.assertion import SnapshotAssertion
from typing_extensions import override

from dmr import Headers, validate
from dmr.negotiation import ContentType
from dmr.openapi import OpenAPIConfig, build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.streaming import StreamingResponse, streaming_response_spec
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _ClassBasedSSE(SSEController[PydanticSerializer]):
    @validate(
        streaming_response_spec(
            SSEvent[int],
            content_type=ContentType.event_stream,
        ),
    )
    async def get(self) -> StreamingResponse:
        raise NotImplementedError

    async def post(self) -> AsyncIterator[SSEvent[int]]:
        raise NotImplementedError


def test_sse_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for SSE."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/sse', _ClassBasedSSE.as_view())],
                ),
                config=OpenAPIConfig(
                    title='SSE Test',
                    version='1.0',
                    openapi_version='3.2.0',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _BaseEvent(pydantic.BaseModel):
    comment: SkipJsonSchema[str | None] = None
    retry: SkipJsonSchema[int | None] = None

    @property
    def should_serialize_data(self) -> bool:
        return True


class _UserEvent(_BaseEvent):
    event: Literal['user'] = 'user'
    id: int
    data: str  # username


class _Payment(pydantic.BaseModel):
    amount: int
    currency: str


class _PaymentEvent(_BaseEvent):
    id: SkipJsonSchema[None] = None
    event: Literal['payment'] = 'payment'
    data: pydantic.Json[_Payment]


_PossibleEvents: TypeAlias = _UserEvent | _PaymentEvent


async def _complex_events(x_header: str) -> AsyncIterator[_PossibleEvents]:
    yield _UserEvent(id=1, data=x_header)
    yield _PaymentEvent(
        data=_Payment(  # pyright: ignore[reportArgumentType]
            amount=10,
            currency='$',
        ).model_dump_json(),
    )


class _HeaderModel(pydantic.BaseModel):
    x_header: str = pydantic.Field(alias='X-Header')


class _ComplexSSE(SSEController[PydanticSerializer]):
    async def get(
        self,
        parsed_headers: Headers[_HeaderModel],
    ) -> AsyncIterator[_PossibleEvents]:
        return _complex_events(parsed_headers.x_header)


@pytest.mark.asyncio
async def test_complex_sse_implementation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/', headers={'X-Header': 'sobolevn'})

    response = await dmr_async_rf.wrap(_ComplexSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert await get_streaming_content(response) == (
        b'id: 1\r\n'
        b'event: user\r\n'
        b'data: "sobolevn"\r\n'
        b'\r\n'
        b'event: payment\r\n'
        b'data: {"amount":10,"currency":"$"}\r\n'
        b'\r\n'
    )


def test_complex_sse_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that complex schema is correct for SSE."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/complex', _ComplexSSE.as_view())],
                ),
                config=OpenAPIConfig(
                    title='SSE Complex Pydantic models',
                    version='1.0',
                    openapi_version='3.2.0',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _OverriddenEvent(pydantic.BaseModel):
    data: bytes
    comment: None = None
    retry: None = None
    event: None = None
    id: None = None

    @property
    def should_serialize_data(self) -> bool:
        return False

    @override
    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: cs.CoreSchema,
        handler: pydantic.GetJsonSchemaHandler,  # noqa: WPS110
    ) -> JsonSchemaValue:
        return {
            'title': 'OverriddenEvent',
            'properties': {
                'data': {
                    'contentSchema': {'type': 'string'},
                },
            },
            'example': {'value': 'data: test'},
        }


async def _overridden_events() -> AsyncIterator[_OverriddenEvent]:
    yield _OverriddenEvent(data=b'test')


class _OverridenSSE(SSEController[PydanticSerializer]):
    async def get(self) -> AsyncIterator[_OverriddenEvent]:
        return _overridden_events()


@pytest.mark.asyncio
async def test_overridden_sse_implementation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_OverridenSSE.as_view()(request))

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert await get_streaming_content(response) == (b'data: test\r\n\r\n')


def test_overridden_sse_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that overridden schema is correct for SSE."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/overridden', _OverridenSSE.as_view())],
                ),
                config=OpenAPIConfig(
                    title='SSE Overridden Pydantic models',
                    version='2.0',
                    openapi_version='3.2.0',
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )
