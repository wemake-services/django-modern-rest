import json
from collections.abc import Sequence
from http import HTTPStatus
from types import MappingProxyType
from typing import Annotated, Any, Final, final

import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from django.http import HttpResponse
from django.urls import path
from faker import Faker
from inline_snapshot import snapshot
from typing_extensions import Sentinel

from dmr import Body, BodyFast, Controller, Headers, modify
from dmr.negotiation import ContentType, conditional_type
from dmr.openapi import build_schema
from dmr.parsers import JsonParser, Parser
from dmr.plugins.msgspec import (
    MsgpackParser,
    MsgpackRenderer,
    MsgspecJsonParser,
    MsgspecSerializer,
)
from dmr.routing import Router
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.types import EMPTY


@final
class _User(msgspec.Struct):
    username: str
    age: int


@final
class _AuthHeaders(msgspec.Struct, rename={'token': 'X-API-Token'}):
    token: str


_HEADERS: Final = MappingProxyType({'X-API-Token': 'token'})

#: Parsers and the location prefix of body errors. `MsgspecJsonParser`
#: parses directly into models, so errors come from the root namespace.
#: `JsonParser` ignores the model and works the default way,
#: like `Body` does: the body is a part of the whole request context.
_parsers = pytest.mark.parametrize(
    ('parsers', 'loc'),
    [
        (EMPTY, ''),
        ([JsonParser()], '.parsed_body'),
    ],
    ids=['fast-msgspec-parser', 'default-json-parser'],
)


def _at(loc: str, path: str = '') -> str:
    full_path = loc + path
    return f' - at `${full_path}`' if full_path else ''


def _make_controller(
    custom_parsers: Sequence[Parser] | Sentinel,
) -> type[Controller[Any]]:
    # Metadata is built when the class is created,
    # so `parsers` must be set in the class body, `EMPTY` means defaults:
    class _ParsersController(Controller[MsgspecSerializer]):
        parsers = custom_parsers

        def put(
            self,
            parsed_headers: Headers[_AuthHeaders],
            parsed_body: BodyFast[_User],
        ) -> _User:
            assert parsed_headers.token
            return parsed_body

    return _ParsersController


@_parsers
def test_body_parses(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
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
def test_body_is_lax_by_default(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
) -> None:
    """Ensures that fast bodies allow type coercion, like regular ones."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': '1'},
        headers=dict(_HEADERS),
    )

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content)['age'] == 1


@_parsers
def test_body_missing_field(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
) -> None:
    """Ensures that error locations depend on the parsing mode."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name()},
        headers=dict(_HEADERS),
    )

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == {
        'detail': [
            {
                'msg': f'Object missing required field `age`{_at(loc)}',
                'type': 'value_error',
            },
        ],
    }


@_parsers
def test_body_wrong_type(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
) -> None:
    """Ensures that nested error locations are preserved."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': 'abc'},
        headers=dict(_HEADERS),
    )

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == {
        'detail': [
            {
                'msg': f'Expected `int`, got `str`{_at(loc, ".age")}',
                'type': 'value_error',
            },
        ],
    }


@_parsers
def test_body_wrong_top_level_type(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
) -> None:
    """Ensures that top level errors point to the body."""
    request = dmr_rf.put('/whatever/', data=[1, 2], headers=dict(_HEADERS))

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == {
        'detail': [
            {
                'msg': f'Expected `object`, got `array`{_at(loc)}',
                'type': 'value_error',
            },
        ],
    }


@_parsers
def test_body_errors_come_first(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
) -> None:
    """
    Ensures that other components are not validated on body errors.

    In the default mode all components are validated together,
    ``msgspec`` reports the first error it finds: headers go first.
    """
    request = dmr_rf.put('/whatever/', data={})  # no headers as well

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    if parsers is EMPTY:
        msg = 'Object missing required field `username`'
    else:
        msg = 'Object missing required field `token` - at `$.parsed_headers`'
    assert json.loads(response.content) == {
        'detail': [{'msg': msg, 'type': 'value_error'}],
    }


@_parsers
def test_other_components_are_validated(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
) -> None:
    """Ensures that other components are validated when body is correct."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': faker.pyint()},
    )

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Object missing required field `token`'
                    ' - at `$.parsed_headers`'
                ),
                'type': 'value_error',
            },
        ],
    })


@_parsers
def test_invalid_json(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
) -> None:
    """Ensures that broken json is still a parsing error."""
    request = dmr_rf.put('/whatever/', data=b'{...', headers=dict(_HEADERS))

    response = _make_controller(parsers).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    # Each parser has its own error message, so we can't use `snapshot()`:
    detail = json.loads(response.content)['detail']
    assert len(detail) == 1
    assert detail[0]['type'] == 'value_error'
    assert 'loc' not in detail[0]


@_parsers
def test_empty_body(
    dmr_rf: DMRRequestFactory,
    *,
    parsers: Sequence[Parser] | Sentinel,
    loc: str,
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
                'msg': 'Expected `object`, got `null` - at `$.parsed_body`',
                'type': 'value_error',
            },
        ],
    })


@final
class _DefaultController(Controller[MsgspecSerializer]):
    def put(self, parsed_body: BodyFast[_User | None] = None) -> bool:
        return parsed_body is None


def test_body_default(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that fast bodies can have defaults."""
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


@final
class _ListController(Controller[MsgspecSerializer]):
    async def put(self, parsed_body: BodyFast[list[_User]]) -> int:
        return len(parsed_body)


@pytest.mark.asyncio
async def test_list_body_async(
    dmr_async_rf: DMRAsyncRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that any model can be used with async endpoints."""
    request = dmr_async_rf.put(
        '/whatever/',
        data=[
            {'username': faker.name(), 'age': faker.pyint()} for _ in range(3)
        ],
    )

    response = await dmr_async_rf.wrap(_ListController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 3


@pytest.mark.asyncio
async def test_list_body_async_error(
    dmr_async_rf: DMRAsyncRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that array locations are preserved."""
    request = dmr_async_rf.put(
        '/whatever/',
        data=[{'username': faker.name(), 'age': faker.pyint()}, {}],
    )

    response = await dmr_async_rf.wrap(_ListController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': ('Object missing required field `username` - at `$[1]`'),
                'type': 'value_error',
            },
        ],
    })


@final
class _Msgpack(msgspec.Struct):
    packed: bool


@final
class _ConditionalController(Controller[MsgspecSerializer]):
    parsers = (MsgspecJsonParser(), MsgpackParser())
    renderers = (MsgpackRenderer(),)

    def put(
        self,
        parsed_body: BodyFast[
            Annotated[
                _User | int,
                conditional_type({
                    ContentType.json: _User,
                    ContentType.msgpack: int,
                }),
            ],
        ],
    ) -> str:
        return type(parsed_body).__name__


def test_conditional_types(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that each content type is parsed into its own model."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': faker.pyint()},
    )
    response = _ConditionalController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert msgspec.msgpack.decode(response.content) == '_User'

    request = dmr_rf.put(
        '/whatever/',
        data=msgspec.msgpack.encode(1),
        headers={'Content-Type': str(ContentType.msgpack)},
    )
    response = _ConditionalController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert msgspec.msgpack.decode(response.content) == 'int'


def test_conditional_types_error(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that ``msgpack`` bodies are validated as well."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name()},
    )
    response = _ConditionalController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert msgspec.msgpack.decode(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Object missing required field `age`',
                'type': 'value_error',
            },
        ],
    })

    request = dmr_rf.put(
        '/whatever/',
        data=msgspec.msgpack.encode('abcd'),
        headers={'Content-Type': str(ContentType.msgpack)},
    )
    response = _ConditionalController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert msgspec.msgpack.decode(response.content) == snapshot({
        'detail': [
            {
                'msg': ('Expected `int | object`, got `str`'),
                'type': 'value_error',
            },
        ],
    })


@final
class _BodyController(Controller[MsgspecSerializer]):
    @modify(operation_id='putUsers')
    def put(
        self,
        parsed_headers: Headers[_AuthHeaders],
        parsed_body: Body[_User],
    ) -> _User:
        raise NotImplementedError


@final
class _FastBodyController(Controller[MsgspecSerializer]):
    @modify(operation_id='putUsers')  # to compare specs with `Body`
    def put(
        self,
        parsed_headers: Headers[_AuthHeaders],
        parsed_body: BodyFast[_User],
    ) -> _User:
        raise NotImplementedError


def test_same_openapi_schema() -> None:
    """Ensures that ``Body`` and ``BodyFast`` have the same OpenAPI spec."""
    fast_schema = build_schema(
        Router('api/', [path('users/', _BodyController.as_view())]),
    ).convert()
    regular_schema = build_schema(
        Router('api/', [path('users/', _FastBodyController.as_view())]),
    ).convert()

    assert fast_schema == regular_schema
    assert fast_schema['paths']['/api/users/']['put']['requestBody']
