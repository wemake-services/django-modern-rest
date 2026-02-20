import dataclasses
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import pytest
from django.http import HttpRequest

from dmr import HeaderSpec, ResponseSpec
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSEContext,
    SSEData,
    SSEResponse,
    SSEStreamingResponse,
    SSEvent,
    validation,
)
from dmr.test import DMRAsyncRequestFactory

if TYPE_CHECKING:
    from tests.test_sse.conftest import GetStreamingContent

serializers: Final[list[type[BaseSerializer]]] = [
    PydanticSerializer,
]

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass
else:  # pragma: no cover
    serializers.append(MsgspecSerializer)


@dataclasses.dataclass(frozen=True, slots=True)
class _User:
    email: str


async def _valid_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    yield SSEvent(
        serializer.serialize(
            _User(email='first@example.com'),
            renderer=renderer,
        ),
    )
    yield SSEvent(
        serializer.serialize(
            _User(email='second@example.com'),
            renderer=renderer,
        ),
    )

    yield b'regular bytes'
    yield b'multiline\nbyte\nstring'
    yield 10


@pytest.mark.asyncio
@pytest.mark.parametrize('serializer', serializers)
async def test_valid_sse(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
    *,
    serializer: type[BaseSerializer],
) -> None:
    """Ensures that valid sse produces valid results."""

    @validation(serializer)
    async def _valid_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        return SSEResponse(_valid_events(serializer, renderer))

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_valid_sse.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert await get_streaming_content(response) == (
        b'data: {"email":"first@example.com"}\r\n'
        b'\r\n'
        b'data: {"email":"second@example.com"}\r\n'
        b'\r\n'
        b'data: regular bytes\r\n'
        b'\r\n'
        b'data: multiline\r\n'
        b'data: byte\r\n'
        b'data: string\r\n'
        b'\r\n'
        b'data: 10\r\n'
        b'\r\n'
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'event',
    [
        {},
        {'a': 'b'},
        [],
        [1, 'a'],
        None,
        'abc',
        object(),
    ],
)
@pytest.mark.parametrize(
    ('options', 'expected'),
    [
        ({'validate_responses': True}, True),
        ({'validate_responses': True, 'validate_events': True}, True),
        ({'validate_responses': False, 'validate_events': True}, True),
        ({'validate_events': True}, True),
        ({}, True),
        ({'validate_responses': False}, False),
        ({'validate_events': False}, False),
        ({'validate_responses': False, 'validate_events': False}, False),
        ({'validate_responses': True, 'validate_events': False}, False),
    ],
)
@pytest.mark.parametrize('serializer', serializers)
async def test_wrong_event_type(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
    *,
    event: Any,
    serializer: type[BaseSerializer],
    options: dict[str, Any],
    expected: bool,
) -> None:
    """Ensures that wrong event types are validated."""

    async def _wrong_type_events(
        serializer: type[BaseSerializer],
        renderer: Renderer,
    ) -> AsyncIterator[SSEData]:
        yield event

    @validation(serializer, **options)
    async def _wrong_type_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        return SSEResponse(_wrong_type_events(serializer, renderer))

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_wrong_type_sse.as_view()(request))

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert response.headers == {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    assert (
        b'event: error\r\n' in await get_streaming_content(response)
    ) is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('options', 'expected'),
    [
        ({'response_spec': None, 'validate_responses': True}, HTTPStatus.OK),
        ({'response_spec': None, 'validate_responses': False}, HTTPStatus.OK),
        (
            {
                'response_spec': ResponseSpec(None, status_code=HTTPStatus.OK),
                'validate_responses': False,
            },
            HTTPStatus.OK,
        ),
        (
            {
                'response_spec': ResponseSpec(
                    None,
                    status_code=HTTPStatus.CONFLICT,
                ),
                'validate_responses': False,
            },
            HTTPStatus.OK,
        ),
        (
            {
                'response_spec': ResponseSpec(
                    SSEData,
                    status_code=HTTPStatus.OK,
                ),
                'validate_responses': False,
            },
            HTTPStatus.OK,
        ),
        (
            {
                'response_spec': ResponseSpec(
                    SSEData,
                    status_code=HTTPStatus.OK,
                    headers={
                        'Cache-Control': HeaderSpec(),
                        'Connection': HeaderSpec(),
                        'X-Accel-Buffering': HeaderSpec(),
                    },
                ),
                'validate_responses': True,
            },
            HTTPStatus.OK,
        ),
        # Failures:
        (
            {
                'response_spec': ResponseSpec(None, status_code=HTTPStatus.OK),
            },
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            {
                'response_spec': ResponseSpec(None, status_code=HTTPStatus.OK),
                'validate_responses': True,
            },
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            {
                'response_spec': ResponseSpec(
                    SSEData,
                    status_code=HTTPStatus.OK,
                    headers={},
                ),
            },
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    ],
)
@pytest.mark.parametrize('serializer', serializers)
async def test_main_response_validation_sse(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    serializer: type[BaseSerializer],
    options: dict[str, Any],
    expected: HTTPStatus,
) -> None:
    """Ensures that response validation can fail."""

    @validation(serializer, **options)
    async def _wrong_sse(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext,
    ) -> SSEResponse:
        return SSEResponse(_valid_events(serializer, renderer))

    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(_wrong_sse.as_view()(request))

    assert response.status_code == expected
