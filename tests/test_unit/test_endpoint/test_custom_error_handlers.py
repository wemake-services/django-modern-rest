import json
from http import HTTPMethod, HTTPStatus
from typing import ClassVar, final

import pydantic
import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from django_modern_rest import (
    Body,
    Controller,
    ResponseDescription,
    modify,
    validate,
)
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

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
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

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == {
        'mode': 'async',
        'message': 'async boom',
    }


class _AsyncValidateErrorHandlerController(Controller[PydanticSerializer]):
    async def async_endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        return self.to_error(str(exc), status_code=HTTPStatus.PAYMENT_REQUIRED)

    @validate(
        ResponseDescription(list[int], status_code=HTTPStatus.OK),
        ResponseDescription(str, status_code=HTTPStatus.PAYMENT_REQUIRED),
        error_handler=async_endpoint_error,
    )
    async def get(self) -> HttpResponse:
        raise ValueError('Error message')


@pytest.mark.asyncio
async def test_validate_async_endpoint_error_for_sync(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensure that async error handler for `@validate` works."""
    request = dmr_async_rf.get('/whatever/', data={})

    response = await dmr_async_rf.wrap(
        _AsyncValidateErrorHandlerController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == 'Error message'


class _ErrorHandlerValidationController(Controller[PydanticSerializer]):
    async def async_endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        # Not `str`:
        return self.to_error(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    @validate(
        ResponseDescription(list[int], status_code=HTTPStatus.OK),
        ResponseDescription(str, status_code=HTTPStatus.PAYMENT_REQUIRED),
        error_handler=async_endpoint_error,
    )
    async def get(self) -> HttpResponse:
        raise ValueError('Error message')


@pytest.mark.asyncio
async def test_validate_error_handler_validation(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensure responses from error handlers are also validated."""
    request = dmr_async_rf.get('/whatever/', data={})

    response = await dmr_async_rf.wrap(
        _ErrorHandlerValidationController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'string_type',
                'loc': [],
                'msg': 'Input should be a valid string',
                'input': 1,
            },
        ],
    })


class _ModifyComplexHandler(Controller[PydanticSerializer]):
    responses: ClassVar[list[ResponseDescription]] = [
        ResponseDescription(str, status_code=HTTPStatus.PAYMENT_REQUIRED),
    ]

    def endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, ValueError):
            return self.to_error(
                'Endpoint',
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            )
        raise exc

    @modify(
        status_code=HTTPStatus.OK,
        error_handler=endpoint_error,
    )
    def get(self) -> int:
        raise ValueError

    @modify(
        status_code=HTTPStatus.OK,
        error_handler=endpoint_error,
    )
    def post(self) -> int:
        raise ZeroDivisionError

    @modify(
        status_code=HTTPStatus.OK,
        error_handler=endpoint_error,
    )
    def put(self) -> int:
        raise RuntimeError('from put')

    @override
    def handle_error(self, endpoint: Endpoint, exc: Exception) -> HttpResponse:
        if isinstance(exc, ZeroDivisionError):
            return self.to_error(
                'Controller',
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            )
        raise exc


@pytest.mark.parametrize(
    ('method', 'expected'),
    [
        (HTTPMethod.GET, 'Endpoint'),
        (HTTPMethod.POST, 'Controller'),
    ],
)
def test_modify_complex_handler(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
    expected: str,
) -> None:
    """Ensure that error handling is layered."""
    request = dmr_rf.generic(str(method), '/whatever/', data=None)

    response = _ModifyComplexHandler.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == expected


def test_modify_global_handler(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that error handling is layered."""
    request = dmr_rf.put('/whatever/', data=None)

    with pytest.raises(RuntimeError, match='from put'):
        _ModifyComplexHandler.as_view()(request)


class _ModifyAsyncComplexHandler(Controller[PydanticSerializer]):
    responses: ClassVar[list[ResponseDescription]] = [
        ResponseDescription(str, status_code=HTTPStatus.PAYMENT_REQUIRED),
    ]

    async def endpoint_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, ValueError):
            return self.to_error(
                'Endpoint',
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            )
        raise exc

    @modify(
        status_code=HTTPStatus.OK,
        error_handler=endpoint_error,
    )
    async def get(self) -> int:
        raise ValueError

    @modify(
        status_code=HTTPStatus.OK,
        error_handler=endpoint_error,
    )
    async def post(self) -> int:
        raise ZeroDivisionError

    @modify(
        status_code=HTTPStatus.OK,
        error_handler=endpoint_error,
    )
    async def put(self) -> int:
        raise RuntimeError('from put')

    @override
    async def handle_async_error(
        self,
        endpoint: Endpoint,
        exc: Exception,
    ) -> HttpResponse:
        if isinstance(exc, ZeroDivisionError):
            return self.to_error(
                'Controller',
                status_code=HTTPStatus.PAYMENT_REQUIRED,
            )
        raise exc


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('method', 'expected'),
    [
        (HTTPMethod.GET, 'Endpoint'),
        (HTTPMethod.POST, 'Controller'),
    ],
)
async def test_modify_async_complex_handler(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    method: HTTPMethod,
    expected: str,
) -> None:
    """Ensure that error handling is layered."""
    request = dmr_async_rf.generic(str(method), '/whatever/', data=None)

    response = await dmr_async_rf.wrap(
        _ModifyAsyncComplexHandler.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == expected


@pytest.mark.asyncio
async def test_modify_async_global_handler(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensure that error handling is layered."""
    request = dmr_async_rf.put('/whatever/', data=None)

    with pytest.raises(RuntimeError, match='from put'):
        await dmr_async_rf.wrap(_ModifyAsyncComplexHandler.as_view()(request))
