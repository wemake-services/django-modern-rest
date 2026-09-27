from collections.abc import AsyncIterator
from typing import Any

from dmr import modify, validate
from dmr.negotiation import ContentType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming import Streaming, StreamingResponse, streaming_response_spec
from dmr.streaming import modify as streaming_modify
from dmr.streaming import validate as streaming_validate
from dmr.streaming.sse import SSEController, SSEvent


async def _valid_events() -> AsyncIterator[SSEvent[bytes]]:
    yield SSEvent(b'multiline\nbyte\nstring', serialize=False)


class InvalidController(SSEController[PydanticSerializer]):
    @validate(
        streaming_response_spec(
            SSEvent[bytes],
            content_type=ContentType.event_stream,
        ),
    )
    async def get(self) -> StreamingResponse:
        # Missing `self.to_stream()`
        return _valid_events()  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

    async def post(self) -> AsyncIterator[Any]:
        # Extra `self.to_stream()`
        return self.to_stream(_valid_events())  # type: ignore[return-value]  # ty: ignore[invalid-return-type]


class ExtrasController(SSEController[PydanticSerializer]):
    extras = Streaming(validate_events=False)

    @streaming_modify(extras=Streaming(validate_events=False))
    async def get(self) -> AsyncIterator[SSEvent[bytes]]:
        return _valid_events()

    streaming_modify(extras=Streaming(validate_events='a'))  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

    streaming_modify(extras=None)  # type: ignore[call-overload]  # ty: ignore[no-matching-overload]

    modify(extras=Streaming(validate_events=False))  # type: ignore[call-overload]  # ty: ignore[no-matching-overload]

    @streaming_validate(
        streaming_response_spec(
            SSEvent[bytes],
            content_type=ContentType.event_stream,
        ),
        extras=Streaming(validate_events=False),
    )
    async def post(self) -> StreamingResponse:
        return self.to_stream(_valid_events())

    streaming_validate(
        streaming_response_spec(
            SSEvent[bytes],
            content_type=ContentType.event_stream,
        ),
        extras=Streaming(validate_events='a'),  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    )

    streaming_validate(  # ty: ignore[no-matching-overload]  # pyrefly: ignore[no-matching-overload]
        streaming_response_spec(
            SSEvent[bytes],
            content_type=ContentType.event_stream,
        ),
        extras=None,  # type: ignore[call-overload]
    )

    validate(  # ty: ignore[no-matching-overload]  # pyrefly: ignore[no-matching-overload]
        streaming_response_spec(
            SSEvent[bytes],
            content_type=ContentType.event_stream,
        ),
        extras=Streaming(validate_events=False),  # type: ignore[call-overload]
    )
