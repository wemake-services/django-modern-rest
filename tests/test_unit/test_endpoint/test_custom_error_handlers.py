import json
from http import HTTPStatus
from typing import ClassVar, cast, final

import pydantic
import pytest
from django.http import HttpResponse
from typing_extensions import override

from django_modern_rest import Body, Controller, ResponseDescription
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import (
    DMRAsyncRequestFactory,
    DMRRequestFactory,
)


@final
class _Payload(pydantic.BaseModel):
    number: int


@final
class _ErrorPayload(pydantic.BaseModel):
    mode: str
    message: str


@final
class _CustomEndpoint(Endpoint):
    """Endpoint with JSON-aware error handlers for tests."""

    @override
    def handle_error(self, exc: Exception) -> HttpResponse:
        return self._controller.to_error(
            {'mode': 'sync', 'message': str(exc)},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @override
    async def handle_async_error(self, exc: Exception) -> HttpResponse:
        return self._controller.to_error(
            {'mode': 'async', 'message': str(exc)},
            status_code=HTTPStatus.BAD_REQUEST,
        )


@final
class _SyncController(Body[_Payload], Controller[PydanticSerializer]):
    endpoint_cls: ClassVar[type[Endpoint]] = _CustomEndpoint
    responses: ClassVar[list[ResponseDescription]] = [
        ResponseDescription(
            _ErrorPayload,
            status_code=HTTPStatus.BAD_REQUEST,
        ),
    ]

    def post(self) -> _Payload:
        raise RuntimeError('sync boom')


@final
class _AsyncController(Body[_Payload], Controller[PydanticSerializer]):
    endpoint_cls: ClassVar[type[Endpoint]] = _CustomEndpoint
    responses: ClassVar[list[ResponseDescription]] = [
        ResponseDescription(
            _ErrorPayload,
            status_code=HTTPStatus.BAD_REQUEST,
        ),
    ]

    async def post(self) -> _Payload:
        raise RuntimeError('async boom')


def test_custom_sync_handle_error(dmr_rf: DMRRequestFactory) -> None:
    """Ensures sync custom error handler returns JSON response."""
    request = dmr_rf.post('/whatever/', data=json.dumps({'number': 1}))

    response = cast(HttpResponse, _SyncController.as_view()(request))

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == {
        'mode': 'sync',
        'message': 'sync boom',
    }


@pytest.mark.asyncio
async def test_custom_async_handle_error(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures async custom error handler returns JSON response."""
    request = dmr_async_rf.post('/whatever/', data=json.dumps({'number': 1}))

    response = cast(
        HttpResponse,
        await dmr_async_rf.wrap(_AsyncController.as_view()(request)),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == {
        'mode': 'async',
        'message': 'async boom',
    }
