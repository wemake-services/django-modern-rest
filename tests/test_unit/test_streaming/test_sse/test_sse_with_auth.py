import json
from collections.abc import AsyncIterator
from http import HTTPStatus

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import DjangoSessionAsyncAuth
from dmr.streaming import StreamingResponse
from dmr.streaming.sse import SSEController, SSEvent
from dmr.test import DMRAsyncRequestFactory
from tests.infra.streaming import get_streaming_content


class _ClassBasedSSE(SSEController[PydanticSerializer]):
    auth = [DjangoSessionAsyncAuth()]

    async def get(self) -> AsyncIterator[SSEvent[bytes]]:
        user = await self.request.auser()
        assert user.is_authenticated
        return self._events(user.get_username())

    async def _events(self, username: str) -> AsyncIterator[SSEvent[bytes]]:
        yield SSEvent(b'user', id=username, serialize=False)


async def _resolve(user: User) -> User:
    return user


@pytest.mark.asyncio
async def test_sse_with_auth_failure(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that incorrect auth raises 401."""
    request = dmr_async_rf.get('/whatever')

    response = await dmr_async_rf.wrap(
        _ClassBasedSSE.as_view()(request),
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
) -> None:
    """Ensures that sse can parse all components with successful auth."""
    request = dmr_async_rf.get('/whatever')
    username = 'test_user'
    request.auser = lambda: _resolve(User(username=username))

    response = await dmr_async_rf.wrap(
        _ClassBasedSSE.as_view()(request),
    )

    assert isinstance(response, StreamingResponse)
    assert response.streaming
    assert response.status_code == HTTPStatus.OK

    expected_content = f'id: {username}\r\ndata: user\r\n\r\n'.encode()
    assert await get_streaming_content(response) == expected_content
