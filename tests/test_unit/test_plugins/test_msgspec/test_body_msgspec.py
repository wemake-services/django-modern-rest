import json
from http import HTTPStatus
from typing import Annotated, Any, Final, final

import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from django.http import HttpRequest, HttpResponse
from django.urls import path
from faker import Faker
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Body, Controller, Headers, modify
from dmr.exceptions import EndpointMetadataError
from dmr.internal.compat import frozen
from dmr.negotiation import ContentType, conditional_type
from dmr.openapi import build_schema
from dmr.parsers import (
    DeserializeFunc,
    FormUrlEncodedParser,
    JsonParser,
    MultiPartParser,
    Parser,
    Raw,
)
from dmr.plugins.msgspec import (
    BodyMsgspec,
    MsgpackParser,
    MsgpackRenderer,
    MsgspecJsonParser,
    MsgspecSerializer,
)
from dmr.routing import Router
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _User(msgspec.Struct):
    username: str
    age: int


@final
class _AuthHeaders(msgspec.Struct, rename={'token': 'X-API-Token'}):
    token: str


_HEADERS: Final = frozen({'X-API-Token': 'token'})


@final
class _HeadersController(Controller[MsgspecSerializer]):
    def put(
        self,
        parsed_headers: Headers[_AuthHeaders],
        parsed_body: BodyMsgspec[_User],
    ) -> _User:
        assert parsed_headers.token
        return parsed_body


def test_body_parses(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that fast bodies are parsed into models."""
    request_data = {'username': faker.name(), 'age': faker.pyint()}
    request = dmr_rf.put(
        '/whatever/',
        data=request_data,
        headers=dict(_HEADERS),
    )

    response = _HeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == request_data


def test_body_is_lax_by_default(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that fast bodies allow type coercion, like regular ones."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': '1'},
        headers=dict(_HEADERS),
    )

    response = _HeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content)['age'] == 1


def test_body_missing_field(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that body errors are not prefixed with ``parsed_body``."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name()},
        headers=dict(_HEADERS),
    )

    response = _HeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == {
        'detail': [
            {
                'msg': 'Object missing required field `age`',
                'type': 'value_error',
            },
        ],
    }


def test_body_wrong_type(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that nested error locations are preserved."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': 'abc'},
        headers=dict(_HEADERS),
    )

    response = _HeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == {
        'detail': [
            {
                'msg': 'Expected `int`, got `str` - at `$.age`',
                'type': 'value_error',
            },
        ],
    }


def test_body_wrong_top_level_type(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that top level body errors have no location."""
    request = dmr_rf.put('/whatever/', data=[1, 2], headers=dict(_HEADERS))

    response = _HeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == {
        'detail': [
            {
                'msg': 'Expected `object`, got `array`',
                'type': 'value_error',
            },
        ],
    }


def test_body_errors_come_first(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that other components are not validated on body errors."""
    request = dmr_rf.put('/whatever/', data={})  # no headers as well

    response = _HeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == {
        'detail': [
            {
                'msg': 'Object missing required field `username`',
                'type': 'value_error',
            },
        ],
    }


def test_other_components_are_validated(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that other components are validated when body is correct."""
    request = dmr_rf.put(
        '/whatever/',
        data={'username': faker.name(), 'age': faker.pyint()},
    )

    response = _HeadersController.as_view()(request)

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


def test_invalid_json(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that broken json is still a parsing error."""
    request = dmr_rf.put('/whatever/', data=b'{...', headers=dict(_HEADERS))

    response = _HeadersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    # Each parser has its own error message, so we can't use `snapshot()`:
    detail = json.loads(response.content)['detail']
    assert len(detail) == 1
    assert detail[0]['type'] == 'value_error'
    assert 'loc' not in detail[0]


def test_empty_body(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that empty bodies are always validated as a part of context."""
    request = dmr_rf.put(
        '/whatever/',
        headers={**_HEADERS, 'Content-Type': 'application/json'},
    )

    response = _HeadersController.as_view()(request)

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


def test_optimized_body_used(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures that fast bodies are optimized."""
    monkeypatch.setattr(
        Controller.endpoint_cls.serializer_context_cls,
        '_noconvert_parse_strategy',
        lambda *args, **kwargs: 1 / 0,  # noqa: WPS344  # pyrefly: ignore[division-by-zero]
    )

    class _OptimizedController(Controller[MsgspecSerializer]):
        def put(self, parsed_body: BodyMsgspec[_User]) -> _User:
            raise NotImplementedError

    request = dmr_rf.put('/whatever/')

    with pytest.raises(ZeroDivisionError):
        _OptimizedController.as_view()(request)


def test_body_optimized(dmr_rf: DMRRequestFactory, faker: Faker) -> None:
    """Ensures that fast bodies work with no default."""

    class _OptimizedController(Controller[MsgspecSerializer]):
        def put(self, parsed_body: BodyMsgspec[_User]) -> _User:
            return parsed_body

    request_data = {'username': faker.name(), 'age': faker.pyint()}
    request = dmr_rf.put(
        '/whatever/',
        data=request_data,
    )
    response = _OptimizedController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == request_data

    request = dmr_rf.put('/whatever/', {})
    response = _OptimizedController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Object missing required field `username`',
                'type': 'value_error',
            },
        ],
    })


@pytest.mark.parametrize(
    'content_type',
    [
        ContentType.json,
        ContentType.msgpack,
    ],
)
def test_empty_body_optimized(
    dmr_rf: DMRRequestFactory,
    *,
    content_type: ContentType,
) -> None:
    """Ensures that empty bodies are validated without other components."""

    class _OptimizedController(Controller[MsgspecSerializer]):
        parsers = (MsgspecJsonParser(), MsgpackParser())

        def put(self, parsed_body: BodyMsgspec[_User]) -> _User:
            raise NotImplementedError

    request = dmr_rf.put(
        '/whatever/',
        headers={'Content-Type': str(content_type)},
    )
    response = _OptimizedController.as_view()(request)

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
    def put(self, parsed_body: BodyMsgspec[_User | None] = None) -> bool:
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

    # Wrong schema still does not work:
    request = dmr_rf.put('/whatever/', {})
    response = _DefaultController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Object missing required field `username`',
                'type': 'value_error',
            },
        ],
    })


@final
class _ListController(Controller[MsgspecSerializer]):
    async def put(self, parsed_body: BodyMsgspec[list[_User]]) -> int:
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
        parsed_body: BodyMsgspec[
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
        parsed_body: BodyMsgspec[_User],
    ) -> _User:
        raise NotImplementedError


def test_same_openapi_schema() -> None:
    """Ensures that ``Body`` and ``BodyMsgspec`` have the same OpenAPI spec."""
    fast_schema = build_schema(
        Router('api/', [path('users/', _BodyController.as_view())]),
    ).convert()
    regular_schema = build_schema(
        Router('api/', [path('users/', _FastBodyController.as_view())]),
    ).convert()

    assert fast_schema == regular_schema
    assert fast_schema['paths']['/api/users/']['put']['requestBody']


def test_other_serializers_are_not_supported() -> None:
    """Ensures that only ``msgspec`` serializer can parse bodies directly."""
    pytest.importorskip('pydantic')

    import pydantic  # noqa: PLC0415

    from dmr.plugins.pydantic import (  # noqa: PLC0415
        PydanticFastSerializer,
        PydanticSerializer,
    )

    class _PydanticUser(pydantic.BaseModel):
        username: str

    for serializer in (PydanticSerializer, PydanticFastSerializer):
        with pytest.raises(EndpointMetadataError, match='uses `BodyMsgspec`'):

            class _PydanticController(
                Controller[serializer],  # type: ignore[valid-type]
            ):
                def put(
                    self,
                    parsed_body: BodyMsgspec[_PydanticUser],
                ) -> _PydanticUser:
                    raise NotImplementedError


@pytest.mark.parametrize(
    'custom_parsers',
    [
        [JsonParser()],
        [FormUrlEncodedParser()],
        [MultiPartParser()],
        [MsgspecJsonParser(), FormUrlEncodedParser()],
    ],
)
def test_parsers_must_decode_into_models(
    custom_parsers: list[Parser],
) -> None:
    """Ensures that only parsers that decode into models are supported."""
    with pytest.raises(
        EndpointMetadataError,
        match=f'{type(custom_parsers[-1]).__qualname__} does not decode into',
    ):

        class _ParsersController(Controller[MsgspecSerializer]):
            parsers = custom_parsers

            def put(self, parsed_body: BodyMsgspec[_User]) -> _User:
                raise NotImplementedError


@final
class _CustomModelParser(Parser):
    __slots__ = ()

    content_type = 'application/json'
    decodes_into_model = True

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        return msgspec.json.decode(to_deserialize, type=model)


@final
class _CustomParserController(Controller[MsgspecSerializer]):
    parsers = (_CustomModelParser(),)

    def put(self, parsed_body: BodyMsgspec[_User]) -> _User:
        return parsed_body


def test_custom_parser_decodes_into_model(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that custom parsers can decode bodies into models."""
    request_data = {'username': faker.name(), 'age': faker.pyint()}
    request = dmr_rf.put('/whatever/', data=request_data)

    response = _CustomParserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == request_data
