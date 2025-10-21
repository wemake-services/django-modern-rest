import json
import sys
from http import HTTPMethod, HTTPStatus
from typing import final

import msgspec
import pytest
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest import (
    Body,
    Controller,
    ResponseDescription,
    modify,
    validate,
)
from django_modern_rest.plugins.msgspec import MsgspecSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _InputModel(msgspec.Struct):
    first_name: str
    last_name: str


@final
class _ReturnModel(msgspec.Struct):
    full_name: str


@final
class _ModelController(
    Controller[MsgspecSerializer],
    Body[_InputModel],
):
    def post(self) -> _ReturnModel:
        first_name = self.parsed_body.first_name
        last_name = self.parsed_body.last_name
        return _ReturnModel(full_name=f'{first_name} {last_name}')


@pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason='3.14 does not fully support msgspec yet',
)
def test_msgspec_model_controller(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that regular parsing works."""
    request_data = {'first_name': faker.name(), 'last_name': faker.last_name()}
    request = dmr_rf.post('/whatever/', data=request_data)

    response = _ModelController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        'full_name': (
            f'{request_data["first_name"]} {request_data["last_name"]}'
        ),
    }


@pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason='3.14 does not fully support msgspec yet',
)
def test_msgspec_model_controller_invalid_input(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that invalid input data raises."""
    request = dmr_rf.post('/whatever/', data={})

    response = _ModelController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'value_error',
                'loc': [],
                'msg': (
                    'Object missing required field `first_name` '
                    '- at `$.parsed_body`'
                ),
            },
        ],
    })


@pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason='3.14 does not fully support msgspec yet',
)
def test_msgspec_model_controller_invalid_types(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that invalid input types raise."""
    request = dmr_rf.post('/whatever/', data={'first_name': 1, 'last_name': 2})

    response = _ModelController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'value_error',
                'loc': [],
                'msg': (
                    'Expected `str`, got `int` - at `$.parsed_body.first_name`'
                ),
            },
        ],
    })


@final
class _OutputController(Controller[MsgspecSerializer]):
    def post(self) -> _ReturnModel:
        return 1  # type: ignore[return-value]

    @modify(status_code=HTTPStatus.CREATED)
    def put(self) -> int:
        return 'a'  # type: ignore[return-value]

    @validate(ResponseDescription(list[int], status_code=HTTPStatus.CREATED))
    def patch(self) -> HttpResponse:
        return self.to_response(['1', '2'], status_code=HTTPStatus.CREATED)


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
    ],
)
def test_msgspec_returns_validated(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that invalid return types raise."""
    request = dmr_rf.generic(str(method), '/whatever/', data={})

    response = _OutputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        response.content
    )
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content)['detail']
