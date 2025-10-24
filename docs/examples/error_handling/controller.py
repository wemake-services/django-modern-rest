from http import HTTPStatus
from typing import ClassVar

import httpx
from django.http import HttpResponse
from typing_extensions import override

from django_modern_rest import (
    Controller,
    ResponseDescription,
)
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.plugins.pydantic import (
    PydanticSerializer,
)


class ProxyController(Controller[PydanticSerializer]):
    responses: ClassVar[list[ResponseDescription]] = [
        # Custom schema that we can return when `HTTPError` happens:
        ResponseDescription(str, status_code=HTTPStatus.FAILED_DEPENDENCY),
    ]

    async def get(self) -> None:
        async with self._client() as client:
            # Simulate some real work:
            await client.get('https://example.com')

    async def post(self) -> None:
        async with self._client() as client:
            # Simulate some real work:
            await client.post('https://example.com', json={})

    @override
    async def handle_async_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        # Will handle errors in all endpoints.
        if isinstance(exc, httpx.HTTPError):
            return self.to_error(
                'Request to example.com failed',
                status_code=HTTPStatus.FAILED_DEPENDENCY,
            )
        # Reraise unfamiliar errors to let someone
        # else to handle them further.
        raise exc

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient()
