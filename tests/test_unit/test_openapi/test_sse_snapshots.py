import json
from collections.abc import AsyncIterator

from django.http import HttpRequest
from django.urls import path
from syrupy.assertion import SnapshotAssertion

from dmr.openapi import OpenAPIConfig, build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.routing import Router
from dmr.sse import SSEContext, SSEData, SSEResponse, sse


async def _events() -> AsyncIterator[SSEData]:  # pragma: no cover
    yield b''


@sse(PydanticSerializer)
async def _valid_sse(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    return SSEResponse(_events())


def test_sse_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for SSE."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/sse', _valid_sse.as_view())],
                    prefix='/api/v1',
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
