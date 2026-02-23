import dataclasses
import json
from collections.abc import AsyncIterator, Sequence
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Final,
    TypeAlias,
)

import pydantic
import pytest
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest, HttpResponse
from typing_extensions import TypedDict

from dmr.components import Cookies, Headers, Path, Query
from dmr.controller import Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.security import AsyncAuth
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
)
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSEContext,
    SSEData,
    SSEResponse,
    SSEStreamingResponse,
    sse,
)
from dmr.test import DMRAsyncRequestFactory

if TYPE_CHECKING:
    from tests.test_sse.conftest import (  # pyright: ignore[reportMissingImports]
        GetStreamingContent,
    )


_Serializes: TypeAlias = list[type[BaseSerializer]]
serializers: Final[_Serializes] = [
    PydanticSerializer,
]

try:
    from dmr.plugins.msgspec import MsgspecSerializer
except ImportError:  # pragma: no cover
    pass  # noqa: WPS420
else:  # pragma: no cover
    serializers.append(MsgspecSerializer)


async def _empty_events(
    serializer: type[BaseSerializer],
    renderer: Renderer,
) -> AsyncIterator[SSEData]:
    # # This is needed to make `_empty_events` an async iterator:
    if False:  # noqa: WPS314
        yield b''  # type: ignore[unreachable]


class _PathModel(TypedDict):
    user_id: int
    stream_name: str


@dataclasses.dataclass
class _QueryModel:
    filter: str


class _HeaderModel(pydantic.BaseModel):
    whatever: str


async def _resolve_user(user: AbstractBaseUser) -> AbstractBaseUser:
    return user


def _get_sse_components_by_auth(
    auth: Sequence[AsyncAuth] | None = None,
) -> type[Controller[PydanticSerializer]]:
    @sse(
        PydanticSerializer,
        path=Path[_PathModel],
        query=Query[_QueryModel],
        headers=Headers[_HeaderModel],
        cookies=Cookies[dict[str, str]],
        auth=auth,
    )
    async def _sse_components(
        request: HttpRequest,
        renderer: Renderer,
        context: SSEContext[
            _PathModel,
            _QueryModel,
            _HeaderModel,
            dict[str, str],
        ],
    ) -> SSEResponse:
        assert context.parsed_path == {'user_id': 1, 'stream_name': 'abc'}
        assert context.parsed_query == _QueryModel(filter='python')
        assert context.parsed_headers == _HeaderModel(whatever='yes')
        assert context.parsed_cookies == {'session_id': 'unique'}
        return SSEResponse(_empty_events(PydanticSerializer, renderer))

    return _sse_components


@pytest.mark.asyncio
async def test_sse_with_auth_failure(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
) -> None:
    """Ensures that incorrect auth raises 401."""
    request = dmr_async_rf.get(
        '/whatever/?filter=python',
        headers={
            'whatever': 'yes',
        },
    )
    request.COOKIES = {
        'session_id': 'unique',
    }
    components = _get_sse_components_by_auth(
        auth=[DjangoSessionAsyncAuth()],
    )

    response = await dmr_async_rf.wrap(
        components.as_view()(request, user_id=1, stream_name='abc'),
    )
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == {
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    }


@pytest.mark.asyncio
async def test_sse_with_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
    django_user_model: type[AbstractBaseUser],
) -> None:
    """Ensures that sse can parse all components with successful auth."""
    request = dmr_async_rf.get(
        '/whatever/?filter=python',
        headers={
            'whatever': 'yes',
        },
    )
    request.COOKIES = {
        'session_id': 'unique',
    }

    user = django_user_model(username='testuser', is_active=True)
    request.auser = lambda: _resolve_user(user)
    components = _get_sse_components_by_auth(
        auth=[DjangoSessionAsyncAuth()],
    )
    response = await dmr_async_rf.wrap(
        components.as_view()(request, user_id=1, stream_name='abc'),
    )

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK
    assert await get_streaming_content(response) == b''
