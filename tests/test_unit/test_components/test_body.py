import json
from http import HTTPStatus
from typing import final

import pydantic
import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from inline_snapshot import snapshot

from dmr import Body, Controller
from dmr.errors import ErrorType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _MyPydanticModel(pydantic.BaseModel):
    age: int


@final
class _WrongPydanticBodyController(
    Controller[PydanticSerializer],
    Body[_MyPydanticModel],
):
    def post(self) -> str:
        raise NotImplementedError


def test_body_parse_wrong_content_type(rf: RequestFactory) -> None:
    """Ensures that body can't be parsed with wrong content type."""
    request = rf.post(
        '/whatever/',
        data={'age': 1},
        headers={'Content-Type': 'application/xml'},
    )

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Cannot parse request body with content type '
                    "'application/xml', expected=['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })


@final
class _WrongAsyncPydanticBodyController(
    Controller[PydanticSerializer],
    Body[_MyPydanticModel],
):
    async def post(self) -> str:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_body_parse_wrong_content_type_async(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that async body can't be parsed with wrong content type."""
    request = dmr_async_rf.post(
        '/whatever/',
        data={'age': 1},
        headers={'Content-Type': 'application/xml'},
    )

    response = await dmr_async_rf.wrap(
        _WrongAsyncPydanticBodyController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Cannot parse request body with content type '
                    "'application/xml', expected=['application/json']"
                ),
                'type': 'value_error',
            },
        ],
    })


def test_body_parse_invalid_json(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that body can't be parsed with invalid json."""
    request = dmr_rf.post(
        '/whatever/',
        data=b'{...',
    )

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    # This test is executed with both `msgspec` and `json` parsers,
    # so we can't use `snapshot()` here:
    assert (
        json.loads(response.content)['detail'][0]['type']
        == ErrorType.value_error
    )
