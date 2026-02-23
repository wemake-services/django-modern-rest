import dataclasses
from collections.abc import AsyncIterator
from typing import TypedDict, assert_type

import pydantic
from django.http import HttpRequest

from dmr.components import Cookies, Headers, Path, Query
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.serializer import BaseSerializer
from dmr.sse import SSEContext, SSEData, SSEResponse, sse


async def _valid_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    yield b'valid event'


class _PathModel(TypedDict):
    user_id: int
    stream_name: str


@dataclasses.dataclass
class _QueryModel:
    filter: str


class _HeaderModel(pydantic.BaseModel):
    whatever: str


@sse(
    PydanticSerializer,
    path=Path[_PathModel],
    query=Query[_QueryModel],
    headers=Headers[_HeaderModel],
    cookies=Cookies[dict[str, str]],
)
async def _sse_valid(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext[
        _PathModel,
        _QueryModel,
        _HeaderModel,
        dict[str, str],
    ],
) -> SSEResponse:
    assert_type(context.parsed_path, _PathModel)
    assert_type(context.parsed_query, _QueryModel)
    assert_type(context.parsed_headers, _HeaderModel)
    assert_type(context.parsed_cookies, dict[str, str])
    return SSEResponse(_valid_events(PydanticSerializer, renderer))


async def _empty_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    yield {}  # type: ignore[misc]


@sse(  # type: ignore[arg-type]
    PydanticSerializer,
    path=Path[_PathModel],
    query=Query[_QueryModel],
    headers=Headers[_HeaderModel],
    cookies=Cookies[dict[str, str]],
)
async def _sse_no_type_args(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    assert_type(context.parsed_path, None)
    assert_type(context.parsed_query, None)
    assert_type(context.parsed_headers, None)
    assert_type(context.parsed_cookies, None)
    return SSEResponse(_valid_events(PydanticSerializer, renderer))


@sse(
    PydanticSerializer,
    path=Path[_PathModel],
    query=Query[_QueryModel],
    cookies=Cookies[dict[str, str]],
)
async def _sse_missing_component(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext[_PathModel, _QueryModel, None, dict[str, str]],
) -> SSEResponse:
    assert_type(context.parsed_path, _PathModel)
    assert_type(context.parsed_query, _QueryModel)
    assert_type(context.parsed_headers, None)
    assert_type(context.parsed_cookies, dict[str, str])
    return SSEResponse(_valid_events(PydanticSerializer, renderer))
