import json
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from django_modern_rest import Body, Controller, Headers, Query
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _MyPydanticModel(pydantic.BaseModel):
    age: int


@final
class _MyTypedDict(TypedDict):
    name: str


@final
class _WrongPydanticBodyController(
    Controller[PydanticSerializer],
    Body[_MyPydanticModel],
):
    """All body of these methods are not correct."""

    def post(self) -> str:  # pragma: no cover
        """Does not respect a body type."""
        return 'done'  # not an exception for a better test clarity


@final
class _WrongTypedDictBodyController(
    Controller[PydanticSerializer],
    Body[_MyTypedDict],
):
    """All body of these methods are not correct."""

    def post(self) -> str:  # pragma: no cover
        """Does not respect a body type."""
        return 'done'  # not an exception for a better test clarity


@final
class _WrongPydanticQueryController(
    Controller[PydanticSerializer],
    Query[_MyPydanticModel],
):
    """All query params of these methods are not correct."""

    def get(self) -> str:  # pragma: no cover
        """Does not respect a body type."""
        return 'done'  # not an exception for a better test clarity


@final
class _MyPydanticHeaders(pydantic.BaseModel):
    timestamp: int = pydantic.Field(alias='X-Timestamp')


@final
class _WrongPydanticHeadersController(
    Controller[PydanticSerializer],
    Headers[_MyPydanticHeaders],
):
    """All headers of these methods are not correct."""

    def get(self) -> str:  # pragma: no cover
        """Does not respect a body type."""
        return 'done'  # not an exception for a better test clarity


def test_validate_pydantic_request_body(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that request body validation works for default settings."""
    request = dmr_rf.post('/whatever/', data={})

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'missing',
                'loc': ['parsed_body', 'age'],
                'msg': 'Field required',
                'input': {},
            },
        ],
    })


def test_validate_typed_dict_request_body(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that request body validation works for default settings."""
    request = dmr_rf.post('/whatever/', data={})

    response = _WrongTypedDictBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'missing',
                'loc': ['parsed_body', 'name'],
                'msg': 'Field required',
                'input': {},
            },
        ],
    })


def test_validate_request_query(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that request query validation works for default settings."""
    request = dmr_rf.get('/whatever/?wrong=1')

    response = _WrongPydanticQueryController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content)['detail']


def test_validate_request_headers(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that request headers validation works for default settings."""
    request = dmr_rf.get('/whatever/', headers={'X-Timestamp': 'not-int'})
    assert 'X-Timestamp' in request.headers

    response = _WrongPydanticHeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'type': 'int_parsing',
                'loc': ['parsed_headers', 'X-Timestamp'],
                'msg': (
                    'Input should be a valid integer, '
                    'unable to parse string as an integer'
                ),
                'input': 'not-int',
            },
        ],
    })
