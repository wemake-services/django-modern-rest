import json
from http import HTTPStatus
from typing import Any

import pydantic
import pytest
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from dmr import Body, Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import (
    PydanticFastSerializer,
)
from dmr.test import DMRRequestFactory
from tests.infra.xml_format import XmlParser, XmlRenderer


class _User(pydantic.BaseModel):
    username: str
    age: int


class _UserController(Controller[PydanticFastSerializer]):
    def put(self, parsed_body: Body[_User]) -> _User:
        return parsed_body


def test_body_parses(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that parsing and rendering works."""
    request_data = {'username': faker.name(), 'age': faker.pyint()}

    request = dmr_rf.put('/whatever/', data=request_data)

    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == request_data


def test_body_error(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that body validation works."""
    request_data = {'username': faker.name()}

    request = dmr_rf.put('/whatever/', data=request_data)

    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_body', 'age'],
                'type': 'value_error',
            },
        ],
    })


def test_invalid_json(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that body validation works."""
    request = dmr_rf.put('/whatever/', data=b'{$(#')

    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Invalid JSON: key must be a string at line 1 column 2',
                'type': 'value_error',
            },
        ],
    })


class _WrongUserController(Controller[PydanticFastSerializer]):
    def get(self) -> _User:
        return {}  # type: ignore[return-value]


def test_response_error(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that response validation works."""
    request = dmr_rf.get('/whatever/')

    response = _WrongUserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['username'],
                'type': 'value_error',
            },
            {'msg': 'Field required', 'loc': ['age'], 'type': 'value_error'},
        ],
    })


class _UnserializableController(Controller[PydanticFastSerializer]):
    def get(self) -> Any:
        return object()


def test_unserializable_error(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that unserializable objects raise."""
    request = dmr_rf.get('/whatever/')

    response = _UnserializableController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error'}],
    })


def test_pydantic_fast_non_json() -> None:
    """Ensures that fast serializer only supports json."""
    with pytest.raises(
        EndpointMetadataError,
        match='serializer does not support',
    ):

        class _RendererController(
            Controller[PydanticFastSerializer],
        ):
            renderers = (XmlRenderer(),)

            def get(self) -> str:
                raise NotImplementedError

    with pytest.raises(
        EndpointMetadataError,
        match='serializer does not support',
    ):

        class _ParserController(
            Controller[PydanticFastSerializer],
        ):
            parsers = (XmlParser(),)

            def get(self) -> str:
                raise NotImplementedError
