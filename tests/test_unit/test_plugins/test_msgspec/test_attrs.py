import enum
import json
import uuid
from http import HTTPStatus

import pytest
from dirty_equals import IsUUID
from django.http import HttpResponse
from django.urls import path
from faker import Faker
from inline_snapshot import snapshot
from syrupy.assertion import SnapshotAssertion

from dmr import Body, Controller
from dmr.openapi import build_schema
from dmr.routing import Router

try:
    import msgspec  # noqa: F401
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

import attrs

from dmr.plugins.msgspec import MsgspecSerializer
from dmr.test import DMRRequestFactory


@attrs.define
class _UserModel:
    email: str
    first_name: str
    last_name: str
    age: int


@enum.unique
class _UserStatus(enum.IntEnum):
    active = 0
    inactive = 1


@attrs.define
class _UserResponseModel(_UserModel):
    uid: uuid.UUID
    status: _UserStatus


class _UserController(
    Controller[MsgspecSerializer],
    Body[_UserModel],
):
    def post(self) -> _UserResponseModel:
        return _UserResponseModel(
            uid=uuid.uuid4(),
            status=_UserStatus.active,
            email=self.parsed_body.email,
            first_name=self.parsed_body.first_name,
            last_name=self.parsed_body.last_name,
            age=self.parsed_body.age,
        )


def test_correct_serializer(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures the correct parsing works."""
    request_data = {
        'email': faker.email(),
        'first_name': faker.name(),
        'last_name': faker.name(),
        'age': faker.pyint(),
    }
    request = dmr_rf.post('/whatever/', data=request_data)
    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == {
        'uid': IsUUID,
        'status': _UserStatus.active.value,
        **request_data,
    }


def test_missing_fields(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures the missing fields raise."""
    request = dmr_rf.post('/whatever/', data={})
    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Object missing required field `email` - at `$.parsed_body`'
                ),
                'type': 'value_error',
            },
        ],
    })


def test_wrong_types_serializer(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures the wrong types raise."""
    request_data = {
        'email': faker.email(),
        'first_name': faker.name(),
        'last_name': faker.name(),
        'age': 'wrong',
    }
    request = dmr_rf.post('/whatever/', data=request_data)
    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Expected `int`, got `str` - at `$.parsed_body.age`',
                'type': 'value_error',
            },
        ],
    })


def test_auth_and_cookies_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for authed and cookies controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/',
                    [path('/cookies', _UserController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _ResponseValidationController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        return 1  # type: ignore[return-value]


def test_wrong_response_validation(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures the wrong types raise."""
    request = dmr_rf.get('/whatever/')
    response = _ResponseValidationController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        response.content
    )
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Expected `str`, got `int`', 'type': 'value_error'}],
    })
