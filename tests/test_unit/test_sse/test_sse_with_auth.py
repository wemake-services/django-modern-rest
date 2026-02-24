import json
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Final,
    TypeAlias,
)

import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from inline_snapshot import snapshot

from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import Renderer
from dmr.security.django_session import (
    DjangoSessionAsyncAuth,
)
from dmr.serializer import BaseSerializer
from dmr.sse import (
    SSEContext,
    SSEData,
    SSEResponse,
    SSEStreamingResponse,
    SSEvent,
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


async def _events(username: str) -> AsyncIterator[SSEData]:
    yield SSEvent(b'user', id=username)


async def _resolve(user: User) -> User:
    return user


@sse(
    PydanticSerializer,
    auth=[DjangoSessionAsyncAuth()],
)
async def _sse_components(
    request: HttpRequest,
    renderer: Renderer,
    context: SSEContext,
) -> SSEResponse:
    user = await request.auser()
    assert user.is_authenticated
    return SSEResponse(_events(user.get_username()))


@pytest.mark.asyncio
async def test_sse_with_auth_failure(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that incorrect auth raises 401."""
    request = dmr_async_rf.get('/whatever')

    response = await dmr_async_rf.wrap(
        _sse_components.as_view()(request),
    )
    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.asyncio
async def test_sse_with_auth_success(
    dmr_async_rf: DMRAsyncRequestFactory,
    get_streaming_content: 'GetStreamingContent',
) -> None:
    """Ensures that sse can parse all components with successful auth."""
    request = dmr_async_rf.get('/whatever')
    username = 'test_user'
    request.auser = lambda: _resolve(User(username=username))

    response = await dmr_async_rf.wrap(
        _sse_components.as_view()(request),
    )

    assert isinstance(response, SSEStreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK

    expected_content = f'id: {username}\r\ndata: user\r\n\r\n'.encode()
    assert await get_streaming_content(response) == expected_content
