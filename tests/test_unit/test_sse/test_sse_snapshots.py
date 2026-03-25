import json
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Literal, TypeAlias

import pydantic
import pytest
from django.http import HttpRequest
from django.urls import path
from pydantic.json_schema import JsonSchemaValue, SkipJsonSchema
from pydantic_core import core_schema as cs
from syrupy.assertion import SnapshotAssertion
from typing_extensions import override

from dmr.openapi import OpenAPIConfig, build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.serializer import BaseSerializer
from dmr.sse import SSEContext, SSEResponse, SSEStreamingResponse, SSEvent, sse
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content

MsgspecSerializer: type[BaseSerializer] | None
try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    MsgspecSerializer = None


async def _events() -> AsyncIterator[SSEvent[int]]:
    yield SSEvent(1)


@sse(PydanticSerializer)
async def _valid_sse(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[int]]:
    return SSEResponse(_events())


@pytest.mark.asyncio
async def test_valid_sse_implemenetation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _valid_sse.as_view()(request),
    )

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert await get_streaming_content(response) == b'data: 1\r\n\r\n'


def test_sse_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for SSE."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/v1/',
                    [path('/sse', _valid_sse.as_view())],
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


async def _complex_events() -> AsyncIterator[_PossibleEvents]:
    yield _UserEvent(id=1, data='sobolevn')
    yield _PaymentEvent(
        data=_Payment(  # pyright: ignore[reportArgumentType]
            amount=10,
            currency='$',
        ).model_dump_json(),
    )


@sse(PydanticSerializer)
async def _complex_sse(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[_PossibleEvents]:
    return SSEResponse(_complex_events())


@pytest.mark.asyncio
async def test_complex_sse_implementation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_complex_sse.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    if MsgspecSerializer is None:  # pragma: no cover
        # Slightly different format:
        assert await get_streaming_content(response) == (
            b'id: 1\r\n'
            b'event: user\r\n'
            b'data: "sobolevn"\r\n'
            b'\r\n'
            b'event: payment\r\n'
            b'data: {"amount": 10, "currency": "$"}\r\n'
            b'\r\n'
        )
    else:  # pragma: no cover
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
                    [path('/complex', _complex_sse.as_view())],
                ),
                config=OpenAPIConfig(
                    title='SSE Complex Pydantic <odels',
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


@sse(PydanticSerializer)
async def _overridden_sse(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[_OverriddenEvent]:
    return SSEResponse(_overridden_events())


@pytest.mark.asyncio
async def test_overridden_sse_implementation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that valid sse produces valid results."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_overridden_sse.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
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
                    [path('/overridden', _overridden_sse.as_view())],
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
