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
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)


from dmr import modify
from dmr.plugins.msgspec import (
    MsgpackParser,
    MsgpackRenderer,
    MsgspecSerializer,
)
from dmr.test import DMRRequestFactory


class _RequestModel(msgspec.Struct):
    username: str
    email: str
    friend_id: int


class _ResponseModel(msgspec.Struct):
    uid: uuid.UUID
    metadata: dict[str, str]
    friends: list[int]


class _MsgpackController(
    Controller[MsgspecSerializer],
    Body[_RequestModel],
):
    @modify(parsers=[MsgpackParser()], renderers=[MsgpackRenderer()])
    def post(self) -> _ResponseModel:
        return _ResponseModel(
            uid=uuid.uuid4(),
            metadata={
                'email': self.parsed_body.email,
                'username': self.parsed_body.username,
            },
            friends=[self.parsed_body.friend_id],
        )


def test_msgpack_correct(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that correct ``msgpack`` request work."""
    request_data = {
        'email': faker.email(),
        'username': faker.name(),
        'friend_id': faker.pyint(),
    }
    request = dmr_rf.post(
        '/whatever/',
        headers={'Content-Type': 'application/msgpack'},
        data=msgspec.msgpack.encode(request_data),
    )

    response = _MsgpackController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/msgpack'}
    assert msgspec.msgpack.decode(response.content) == {
        'uid': IsUUID,
        'metadata': {
            'email': request_data['email'],
            'username': request_data['username'],
        },
        'friends': [request_data['friend_id']],
    }


def test_msgpack_missing_fields(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures ``msgpack`` request with empty body work."""
    request = dmr_rf.post(
        '/whatever/',
        headers={'Content-Type': 'application/msgpack'},
        data=msgspec.msgpack.encode({}),
    )

    response = _MsgpackController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/msgpack'}
    assert msgspec.msgpack.decode(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Object missing required field `username` '
                    '- at `$.parsed_body`'
                ),
                'type': 'value_error',
            },
        ],
    })


def test_msgpack_wrong_bytes(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures ``msgpack`` request with wrong bytes raise correctly."""
    request = dmr_rf.post(
        '/whatever/',
        headers={'Content-Type': 'application/msgpack'},
        data=b'{..@7{!',
    )

    response = _MsgpackController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/msgpack'}
    assert msgspec.msgpack.decode(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'MessagePack data is malformed: '
                    'trailing characters (byte 1)'
                ),
                'type': 'value_error',
            },
        ],
    })


def test_msgpack_schema(snapshot: SnapshotAssertion) -> None:
    """Ensure that schema is correct for msgpack controller."""
    assert (
        json.dumps(
            build_schema(
                Router(
                    'api/',
                    [path('/msgpack', _MsgpackController.as_view())],
                ),
            ).convert(),
            indent=2,
        )
        == snapshot
    )


class _MsgpackWrongController(Controller[MsgspecSerializer]):
    @modify(renderers=[MsgpackRenderer()])
    def get(self) -> str:
        return 1  # type: ignore[return-value]


def test_msgpack_response_validation(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures ``msgpack`` request with wrong responses validates."""
    request = dmr_rf.get('/whatever/')

    response = _MsgpackWrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY, (
        response.content
    )
    assert response.headers == {'Content-Type': 'application/msgpack'}
    assert msgspec.msgpack.decode(response.content) == snapshot({
        'detail': [{'msg': 'Expected `str`, got `int`', 'type': 'value_error'}],
    })


class _MsgpackNoneController(Controller[MsgspecSerializer], Body[None]):
    @modify(
        parsers=[MsgpackParser()],
        renderers=[MsgpackRenderer()],
        status_code=HTTPStatus.NO_CONTENT,
    )
    def post(self) -> None:
        """Return `None`."""


def test_msgpack_explicit_none(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures ``msgpack`` handles ``None`` annotation correctly."""
    request = dmr_rf.post(
        '/whatever/',
        headers={'Content-Type': 'application/msgpack'},
        data=b'',
    )

    response = _MsgpackNoneController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT, response.content
    assert response.headers == {'Content-Type': 'application/msgpack'}
    assert response.content == b''
