import json
from collections.abc import Sequence
from http import HTTPStatus
from typing import ClassVar, final

import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Controller, ResponseSpec
from dmr.endpoint import Endpoint
from dmr.errors import ErrorModel
from dmr.exceptions import InternalServerError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _UndeclaredSyncController(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise InternalServerError('database is down')


@final
class _UndeclaredAsyncController(Controller[PydanticSerializer]):
    async def get(self) -> str:
        raise InternalServerError('database is down')


def test_sync_undeclared_error_status(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that our own errors don't have to be described by the user."""
    request = dmr_rf.get('/whatever/')

    response = _UndeclaredSyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error'}],
    })


@pytest.mark.asyncio
async def test_async_undeclared_error_status(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that our own errors don't have to be described by the user."""
    request = dmr_async_rf.get('/whatever/')

    response = await dmr_async_rf.wrap(
        _UndeclaredAsyncController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error'}],
    })


@final
class _DeclaredController(Controller[PydanticSerializer]):
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(ErrorModel, status_code=HTTPStatus.INTERNAL_SERVER_ERROR),
    )

    def get(self) -> str:
        raise InternalServerError('database is down')


def test_declared_error_status(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that describing our error status code still works."""
    request = dmr_rf.get('/whatever/')

    response = _DeclaredController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error'}],
    })


@final
class _WronglyDeclaredController(Controller[PydanticSerializer]):
    # Our errors are `ErrorModel` objects, not lists of integers:
    responses: ClassVar[Sequence[ResponseSpec]] = (
        ResponseSpec(list[int], status_code=HTTPStatus.INTERNAL_SERVER_ERROR),
    )

    def get(self) -> str:
        raise InternalServerError('database is down')


def test_wrongly_declared_error_status(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that describing a status code brings the validation back."""
    request = dmr_rf.get('/whatever/')

    response = _WronglyDeclaredController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@final
class _CustomHandlerController(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise ZeroDivisionError

    @override
    def handle_error(
        self,
        endpoint: Endpoint,
        controller: 'Controller[PydanticSerializer]',
        exc: Exception,
    ) -> HttpResponse:
        return self.to_error(
            'custom',
            status_code=HTTPStatus.NOT_IMPLEMENTED,
        )


def test_custom_handler_status_is_validated(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that user's own error responses are still validated."""
    request = dmr_rf.get('/whatever/')

    response = _CustomHandlerController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Returned status code 501 is not specified in the list '
                    'of allowed status codes: [200, 422, 406]'
                ),
                'type': 'value_error',
            },
        ],
    })
