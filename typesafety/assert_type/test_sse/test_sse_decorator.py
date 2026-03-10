import dataclasses
from collections.abc import AsyncIterator
from typing import TypedDict, assert_type

import pydantic
from django.http import HttpRequest

from dmr.components import Cookies, Headers, Path, Query
from dmr.plugins.pydantic import PydanticSerializer
from dmr.sse import SSEContext, SSEResponse, SSEvent, sse


async def _valid_events() -> AsyncIterator[SSEvent[bytes]]:
    yield SSEvent(b'valid event', serialize=False)


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
    context: SSEContext[
        _PathModel,
        _QueryModel,
        _HeaderModel,
        dict[str, str],
    ],
) -> SSEResponse[SSEvent[bytes]]:
    assert_type(context.parsed_path, _PathModel)
    assert_type(context.parsed_query, _QueryModel)
    assert_type(context.parsed_headers, _HeaderModel)
    assert_type(context.parsed_cookies, dict[str, str])
    return SSEResponse(_valid_events())


@sse(  # type: ignore[arg-type]
    PydanticSerializer,
    path=Path[_PathModel],
    query=Query[_QueryModel],
    headers=Headers[_HeaderModel],
    cookies=Cookies[dict[str, str]],
)
async def _sse_no_type_args(
    request: HttpRequest,
    context: SSEContext,
) -> SSEResponse[SSEvent[bytes]]:
    assert_type(context.parsed_path, None)
    assert_type(context.parsed_query, None)
    assert_type(context.parsed_headers, None)
    assert_type(context.parsed_cookies, None)
    return SSEResponse(_valid_events())


@sse(
    PydanticSerializer,
    path=Path[_PathModel],
    query=Query[_QueryModel],
    cookies=Cookies[dict[str, str]],
)
async def _sse_missing_component(
    request: HttpRequest,
    context: SSEContext[_PathModel, _QueryModel, None, dict[str, str]],
) -> SSEResponse[SSEvent[bytes]]:
    assert_type(context.parsed_path, _PathModel)
    assert_type(context.parsed_query, _QueryModel)
    assert_type(context.parsed_headers, None)
    assert_type(context.parsed_cookies, dict[str, str])
    return SSEResponse(_valid_events())
