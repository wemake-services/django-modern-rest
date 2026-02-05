import datetime as dt
import json
import uuid
from http import HTTPStatus
from typing import Any, ClassVar, final

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest import Body, Controller
from django_modern_rest.plugins.pydantic import (
    ModelDumpKwargs,
    PydanticSerializer,
)
from django_modern_rest.test import DMRRequestFactory


@final
class _BodyModel(pydantic.BaseModel):
    uid: uuid.UUID
    email: pydantic.EmailStr
    created_at: dt.datetime
    elapsed: dt.timedelta
    url: pydantic.HttpUrl
    extra: pydantic.Json[Any]


@final
class _ComplexFieldsController(
    Controller[PydanticSerializer],
    Body[_BodyModel],
):
    def post(self) -> _BodyModel:
        return self.parsed_body


def test_complex_pydantic_serialization(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures by default all complex fields work."""
    request_data = {
        'uid': uuid.uuid4(),
        'email': faker.email(),
        'created_at': faker.future_datetime(),
        'elapsed': faker.time_delta(),
        'url': faker.url(),
        'extra': '{"key": "value"}',
    }

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _ComplexFieldsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content).keys() == request_data.keys()
    assert json.loads(response.content)['extra'] == {'key': 'value'}


@final
class _RoundTripPydanticSerializer(PydanticSerializer):
    model_dump_kwargs: ClassVar[ModelDumpKwargs] = {
        **PydanticSerializer.model_dump_kwargs,
        'round_trip': True,
    }


@final
class _RoundTripJsonFieldController(
    Controller[_RoundTripPydanticSerializer],
    Body[_BodyModel],
):
    def post(self) -> _BodyModel:
        return self.parsed_body


def test_pydantic_round_trip_json_field(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures by round trip json field works."""
    request_data = {
        'uid': uuid.uuid4(),
        'email': faker.email(),
        'created_at': faker.future_datetime(),
        'elapsed': faker.time_delta(),
        'url': faker.url(),
        'extra': '{"key": "value"}',
    }

    request = dmr_rf.post('/whatever/', data=request_data)

    response = _RoundTripJsonFieldController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content).keys() == request_data.keys()
    assert json.loads(response.content)['extra'] == '{"key":"value"}'


@final
class _User:
    """Class that can't be deserialized or serialized by default."""


@final
class _ArbitraryTypesModel(pydantic.BaseModel):
    user: _User

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)


@final
class _ArbitraryTypesInputController(
    Controller[PydanticSerializer],
    Body[_ArbitraryTypesModel],
):
    def post(self) -> int:
        raise NotImplementedError


def test_complex_pydantic_in_arbitrary_types(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures by arbitrary types in pydantic produce clear errors."""
    request = dmr_rf.post('/whatever/', data={'user': 1})

    response = _ArbitraryTypesInputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Input should be an instance of _User',
                'loc': ['parsed_body', 'user'],
                'type': 'value_error',
            },
        ],
    })


@final
class _ArbitraryTypesOutputController(
    Controller[PydanticSerializer],
):
    def post(self) -> _ArbitraryTypesModel:
        return _ArbitraryTypesModel(user=_User())


def test_pydantic_arbitrary_types(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures by arbitrary types in pydantic produce clear errors."""
    request = dmr_rf.post('/whatever/', data={})

    response = _ArbitraryTypesOutputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error'}],
    })


def test_pydantic_arbitrary_types_debug(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures by arbitrary types in pydantic produce clear errors in debug."""
    settings.DEBUG = True
    request = dmr_rf.post('/whatever/', data={})

    response = _ArbitraryTypesOutputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Unable to serialize unknown type: '
                    "<class 'test_complex_pydantic_fields._User'>"
                ),
            },
        ],
    })


@final
class _ObjectOutputController(
    Controller[PydanticSerializer],
):
    def post(self) -> object:
        return object()


def test_complex_pydantic_out_object(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures by arbitrary types in pydantic produce clear errors."""
    request = dmr_rf.post('/whatever/', data={})

    response = _ObjectOutputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Internal server error'}],
    })


@pytest.mark.parametrize(
    ('typ', 'return_value'),
    [
        (set[int], {1, 2}),
        (frozenset[str], frozenset(('a', 'b'))),
        (tuple[str, ...], ('a', 'b')),
    ],
)
def test_complex_pydantic_out_valid_object(
    dmr_rf: DMRRequestFactory,
    *,
    typ: Any,
    return_value: Any,
) -> None:
    """Ensures by most builtin types work."""

    class _TypeOutputController(Controller[PydanticSerializer]):
        def get(self) -> typ:  # pyright: ignore[reportInvalidTypeForm]
            return return_value

    request = dmr_rf.get('/whatever/', data={})

    response = _TypeOutputController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content)
