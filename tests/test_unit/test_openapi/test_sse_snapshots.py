import json
from collections.abc import AsyncIterator
from typing import Literal, TypeAlias

import pydantic
from django.http import HttpRequest
from django.urls import path
from pydantic.json_schema import SkipJsonSchema
from syrupy.assertion import SnapshotAssertion

from dmr.openapi import OpenAPIConfig, build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.routing import Router
from dmr.sse import SSEContext, SSEResponse, SSEvent, sse


async def _events() -> AsyncIterator[SSEvent[int]]:  # pragma: no cover
    yield SSEvent(1)


@sse(PydanticSerializer)
async def _valid_sse(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse[SSEvent[int]]:
    raise NotImplementedError


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


class _BaseEvent(pydantic.BaseModel):
    comment: SkipJsonSchema[str | None] = None
    retry: SkipJsonSchema[int | None] = None

    @property
    def serialize(self) -> bool:
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


_MySSE: TypeAlias = _UserEvent | _PaymentEvent


async def _complex_events() -> AsyncIterator[_MySSE]:
    yield _UserEvent(id=1, data='sobolevn')
    yield _PaymentEvent(data=_Payment(amount=10, currency='$'))


@sse(PydanticSerializer)
async def _complex_sse(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse[_MySSE]:
    return SSEResponse(_complex_events())


def test_complex_sse_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that complex schema is correct for SSE."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    [path('/complex', _complex_sse.as_view())],
                    prefix='/api/v1',
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
