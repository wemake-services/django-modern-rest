import json
from http import HTTPStatus
from typing import Any

import pydantic
import pytest
from dirty_equals import IsStr
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from dmr import Body, Controller, modify
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.plugins.pydantic import serializer as pydantic_serializer
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
    # `msg` can change if `msgspec` is present or not:
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': IsStr(),
                'type': 'value_error',
            },
        ],
    })


def test_invalid_json_native(
    dmr_rf: DMRRequestFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures that body validation works with native json."""
    monkeypatch.setattr(
        pydantic_serializer,
        '_json_loads',
        pydantic_serializer._get_cached_type_adapter(Any).validate_json,
    )

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


def test_response_error(dmr_rf: DMRRequestFactory) -> None:
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


def test_unserializable_error(dmr_rf: DMRRequestFactory) -> None:
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


class _EmptyBodyController(Controller[PydanticFastSerializer]):
    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self, parsed_body: Body[None]) -> None:
        """Does not return anything."""


def test_empty_json_body(
    dmr_rf: DMRRequestFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures that body can be empty with both modes."""
    request = dmr_rf.post(
        '/whatever/',
        data=b'',
        headers={'Content-Type': 'application/json'},
    )

    response = _EmptyBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.content == b''


def test_empty_json_body_native(
    dmr_rf: DMRRequestFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures that body can be empty with both modes."""
    monkeypatch.setattr(
        pydantic_serializer,
        '_json_loads',
        pydantic_serializer._get_cached_type_adapter(Any).validate_json,
    )

    request = dmr_rf.post(
        '/whatever/',
        data=b'',
        headers={'Content-Type': 'application/json'},
    )

    response = _EmptyBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.content == b''
