import json
from collections.abc import Sequence
from http import HTTPStatus
from types import MappingProxyType
from typing import Any, Final, final

import pydantic
import pytest
from django.http import HttpResponse
from django.urls import path
from faker import Faker
from inline_snapshot import snapshot
from typing_extensions import Sentinel

from dmr import Body, BodyFast, Controller, Headers, modify
from dmr.errors import ErrorDetail, ErrorType
from dmr.exceptions import EndpointMetadataError
from dmr.openapi import build_schema
from dmr.parsers import JsonParser, Parser
from dmr.plugins.pydantic import PydanticFastSerializer, PydanticSerializer
from dmr.routing import Router
from dmr.test import DMRRequestFactory
from dmr.types import EMPTY


@final
class _User(pydantic.BaseModel):
    username: str
    age: int


@final
class _AuthHeaders(pydantic.BaseModel):
    token: str = pydantic.Field(alias='X-API-Token')


_HEADERS: Final = MappingProxyType({'X-API-Token': 'token'})

#: `PydanticFastSerializer` ignores parsers, so any parser is fast:
_parsers: Final = pytest.mark.parametrize(
    'parsers',
    [EMPTY, [JsonParser()]],
    ids=['default-parser', 'json-parser'],
)


def _headers_error() -> ErrorDetail:
    return {
        'msg': 'Field required',
        'loc': ['parsed_headers', 'X-API-Token'],
        'type': str(ErrorType.value_error),
    }


def _make_controller(
    custom_parsers: Sequence[Parser] | Sentinel,
) -> type[Controller[Any]]:
    # Metadata is built when the class is created,
    # so `parsers` must be set in the class body, `EMPTY` means defaults:
    class _UserController(Controller[PydanticFastSerializer]):
        parsers = custom_parsers

        def put(
            self,
            parsed_headers: Headers[_AuthHeaders],
            parsed_body: BodyFast[_User],
        ) -> _User:
            assert parsed_headers.token
            return parsed_body

    return _UserController


@_parsers
def test_body_parses(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    parsers: Sequence[Parser] | Sentinel,
) -> None:
    """Ensures that fast bodies are parsed into models."""
    request_data = {'username': faker.name(), 'age': faker.pyint()}
    request = dmr_rf.put(
        '/whatever/',
        data=request_data,
        headers=dict(_HEADERS),
    )

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == request_data


@_parsers
def test_body_errors(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
) -> None:
    """Ensures that error locations start from the root namespace."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': 1, 'age': 'abc'},
        headers=dict(_HEADERS),
    )

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be a valid string',
                'loc': ['username'],
                'type': 'value_error',
            },
            {
                'msg': (
                    'Input should be a valid integer, '
                    'unable to parse string as an integer'
                ),
                'loc': ['age'],
                'type': 'value_error',
            },
        ],
    })


@_parsers
def test_body_wrong_top_level_type(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
) -> None:
    """Ensures that top level errors have no location at all."""
    request = dmr_rf.put('/whatever/', data=[1, 2], headers=dict(_HEADERS))

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be an object',
                'loc': [],
                'type': 'value_error',
            },
        ],
    })


@_parsers
def test_body_errors_come_first(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
) -> None:
    """Ensures that other components are not validated on body errors."""
    request = dmr_rf.put('/whatever/', data={})  # no headers as well

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['username'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['age'],
                'type': 'value_error',
            },
        ],
    })


@_parsers
def test_other_components_are_validated(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    parsers: Sequence[Parser] | Sentinel,
) -> None:
    """Ensures that other components are validated when body is correct."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': faker.pyint()},
    )

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == {'detail': [_headers_error()]}


@_parsers
def test_invalid_json(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
) -> None:
    """Ensures that broken json is still a parsing error."""
    request = dmr_rf.put('/whatever/', data=b'{...', headers=dict(_HEADERS))

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Invalid JSON: key must be a string at line 1 column 2'
                ),
                'type': 'value_error',
            },
        ],
    })


@_parsers
def test_empty_body(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
) -> None:
    """Ensures that empty bodies are always validated as a part of context."""
    request = dmr_rf.put(
        '/whatever/',
        headers={**_HEADERS, 'Content-Type': 'application/json'},
    )

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Input should be a valid dictionary or instance of _User'
                ),
                'loc': ['parsed_body'],
                'type': 'value_error',
            },
        ],
    })


@_parsers
def test_body_default(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    parsers: Sequence[Parser] | Sentinel,
) -> None:
    """Ensures that fast bodies can have defaults."""
    custom_parsers = parsers  # class bodies can't reuse the same name

    class _DefaultController(Controller[PydanticFastSerializer]):
        parsers = custom_parsers

        def put(self, parsed_body: BodyFast[_User | None] = None) -> bool:
            return parsed_body is None

    request = dmr_rf.put('/whatever/')
    response = _DefaultController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) is True

    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': faker.pyint()},
    )
    response = _DefaultController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) is False


def test_regular_serializer_is_not_supported() -> None:
    """Ensures that the regular serializer rejects fast bodies."""
    with pytest.raises(EndpointMetadataError, match='uses `BodyFast`'):

        class _RegularController(Controller[PydanticSerializer]):
            def put(self, parsed_body: BodyFast[_User]) -> _User:
                raise NotImplementedError

    with pytest.raises(EndpointMetadataError, match='uses `BodyFast`'):

        class _RegularDefaultController(Controller[PydanticSerializer]):
            def put(
                self,
                parsed_body: BodyFast[_User | None] = None,
            ) -> _User | None:
                raise NotImplementedError


def test_same_openapi_schema() -> None:
    """Ensures that ``Body`` and ``BodyFast`` have the same OpenAPI spec."""

    class _BodyController(Controller[PydanticFastSerializer]):
        @modify(operation_id='putUsers')  # names differ, ids must not
        def put(
            self,
            parsed_headers: Headers[_AuthHeaders],
            parsed_body: Body[_User],
        ) -> _User:
            raise NotImplementedError

    class _BodyFastController(Controller[PydanticFastSerializer]):
        @modify(operation_id='putUsers')
        def put(
            self,
            parsed_headers: Headers[_AuthHeaders],
            parsed_body: BodyFast[_User],
        ) -> _User:
            raise NotImplementedError

    def build(controller: type[Controller[Any]]) -> dict[str, Any]:
        return build_schema(
            Router('api/', [path('users/', controller.as_view())]),
        ).convert()

    fast_schema = build(_BodyFastController)
    assert fast_schema == build(_BodyController)
    assert fast_schema['paths']['/api/users/']['put']['requestBody']
