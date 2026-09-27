import json
from http import HTTPStatus
from typing import Annotated, Any, Final, Literal, TypeAlias, final

import pydantic
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test.client import MULTIPART_CONTENT
from typing_extensions import TypedDict, override

from dmr import (
    Body,
    Controller,
    Cookies,
    FileMetadata,
    Headers,
    Path,
    Query,
)
from dmr.components import ComponentParser
from dmr.endpoint import Endpoint
from dmr.negotiation import ContentType, conditional_type
from dmr.parsers import FormUrlEncodedParser, JsonParser, MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory
from dmr.types import EMPTY
from tests.infra.xml_format import XmlParser

_JSON: Final = 'application/json'


class _Model(TypedDict):
    name: str


@final
class _FrozenModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    name: str = 'frozen'


@final
class _MutableModel(pydantic.BaseModel):
    name: str = 'mutable'


#: Default value must be passed as-is, we check it by identity:
_FROZEN_DEFAULT: Final = _FrozenModel()
_QUERY_DEFAULT: Final = _FrozenModel(name='query')

serializers: list[Any] = [PydanticSerializer]
#: Models for each serializer, since `msgspec` needs a `Struct` for headers:
models: list[Any] = [_Model]
#: Non-frozen models are rejected as defaults by model constructors:
mutable_defaults: list[Any] = [(PydanticSerializer, _MutableModel())]

try:
    import msgspec
except ImportError:  # pragma: no cover
    pass  # do nothing then :(  # noqa: WPS420
else:
    from dmr.plugins.msgspec import MsgspecSerializer

    class _StructModel(msgspec.Struct):
        name: str

    class _MutableStruct(msgspec.Struct):
        name: str = 'mutable'

    serializers.append(MsgspecSerializer)
    models.append(_StructModel)
    mutable_defaults.append((MsgspecSerializer, _MutableStruct()))


class _FileInfo(TypedDict):
    name: str


class _FileModel(TypedDict):
    rules: _FileInfo


def _build_controller(
    serializer: type[BaseSerializer],
    model: Any,
) -> type[Controller]:  # type: ignore[type-arg]
    class _DefaultsController(Controller[serializer]):  # type: ignore[valid-type]
        def post(  # noqa: WPS211
            self,
            parsed_body: Body[model | None] = None,  # pyright: ignore[reportInvalidTypeForm]
            parsed_query: Query[model | None] = None,  # pyright: ignore[reportInvalidTypeForm]
            parsed_headers: Headers[model | None] = None,  # pyright: ignore[reportInvalidTypeForm]
            parsed_cookies: Cookies[model | None] = None,  # pyright: ignore[reportInvalidTypeForm]
            *,
            parsed_path: Path[model | None] = None,  # pyright: ignore[reportInvalidTypeForm]
        ) -> dict[str, Any]:
            return {
                'body': parsed_body,
                'query': parsed_query,
                'headers': parsed_headers,
                'cookies': parsed_cookies,
                'path': parsed_path,
            }

    return _DefaultsController


@pytest.mark.parametrize(
    ('serializer', 'model'),
    list(zip(serializers, models, strict=True)),
)
def test_all_defaults(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
    model: Any,
) -> None:
    """Ensures that all components use defaults when there's no data."""
    request = dmr_rf.post('/whatever/')
    # There are no headers at all in this request:
    request.META = {}

    response = _build_controller(serializer, model).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == {
        'body': None,
        'query': None,
        'headers': None,
        'cookies': None,
        'path': None,
    }


@pytest.mark.parametrize(
    ('serializer', 'model'),
    list(zip(serializers, models, strict=True)),
)
def test_all_provided(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
    model: Any,
) -> None:
    """Ensures that all components are parsed when there's data."""
    request = dmr_rf.post(
        '/whatever/?name=query',
        data=b'{"name": "body"}',
        content_type=_JSON,
        headers={'name': 'headers'},
    )
    request.COOKIES = {'name': 'cookies'}

    response = _build_controller(serializer, model).as_view()(
        request,
        name='path',
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == {
        'body': {'name': 'body'},
        'query': {'name': 'query'},
        'headers': {'name': 'headers'},
        'cookies': {'name': 'cookies'},
        'path': {'name': 'path'},
    }


@pytest.mark.parametrize(
    ('serializer', 'model'),
    list(zip(serializers, models, strict=True)),
)
def test_invalid_data_with_defaults(
    dmr_rf: DMRRequestFactory,
    *,
    serializer: type[BaseSerializer],
    model: Any,
) -> None:
    """Ensures that defaults do not disable validation of provided data."""
    request = dmr_rf.post(
        '/whatever/',
        data=b'{"other": "body"}',
        content_type=_JSON,
    )

    response = _build_controller(serializer, model).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert 'parsed_body' in response.content.decode()


@final
class _ModelDefaultsController(Controller[PydanticSerializer]):
    """Defaults of the same type as the model, not just ``None``."""

    parsers = (JsonParser(), FormUrlEncodedParser(), MultiPartParser())

    def post(
        self,
        parsed_body: Body[_FrozenModel] = _FROZEN_DEFAULT,
        parsed_query: Query[_FrozenModel] = _QUERY_DEFAULT,
        help_text: str = 'regular default',
    ) -> dict[str, Any]:
        return {
            'body': parsed_body.name,
            # Defaults are passed as-is, without any copies:
            'body_is_default': parsed_body is _FROZEN_DEFAULT,
            'query': parsed_query.name,
            'help_text': help_text,
        }


@pytest.mark.parametrize(
    ('request_kwargs', 'expected'),
    [
        (
            {},
            {
                'body': 'frozen',
                'body_is_default': True,
                'query': 'query',
                'help_text': 'regular default',
            },
        ),
        (
            {'data': b'', 'content_type': _JSON},
            {
                'body': 'frozen',
                'body_is_default': True,
                'query': 'query',
                'help_text': 'regular default',
            },
        ),
        (
            {'data': b'{"name": "json"}', 'content_type': _JSON},
            {
                'body': 'json',
                'body_is_default': False,
                'query': 'query',
                'help_text': 'regular default',
            },
        ),
        (
            {'data': {}, 'content_type': MULTIPART_CONTENT},
            {
                'body': 'frozen',
                'body_is_default': True,
                'query': 'query',
                'help_text': 'regular default',
            },
        ),
        (
            {'data': {'name': 'form'}, 'content_type': MULTIPART_CONTENT},
            {
                'body': 'form',
                'body_is_default': False,
                'query': 'query',
                'help_text': 'regular default',
            },
        ),
        (
            {
                'data': 'name=urlencoded',
                'content_type': 'application/x-www-form-urlencoded',
            },
            {
                'body': 'urlencoded',
                'body_is_default': False,
                'query': 'query',
                'help_text': 'regular default',
            },
        ),
    ],
)
def test_model_defaults(
    dmr_rf: DMRRequestFactory,
    *,
    request_kwargs: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """Ensures that non-``None`` defaults and regular parameters work."""
    request = dmr_rf.post('/whatever/', **request_kwargs)

    response = _ModelDefaultsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == expected


def test_model_defaults_with_query(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that query default is replaced with real data."""
    request = dmr_rf.post('/whatever/?name=real')

    response = _ModelDefaultsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content)['query'] == 'real'


def test_body_null_is_not_default(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that json `null` body is parsed, it is not a missing body."""
    request = dmr_rf.post('/whatever/', data=b'null', content_type=_JSON)

    response = _ModelDefaultsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content


@pytest.mark.parametrize(('serializer', 'default'), mutable_defaults)
def test_mutable_default_is_rejected(
    *,
    serializer: type[BaseSerializer],
    default: Any,
) -> None:
    """
    Ensures that mutable defaults are rejected by the model constructors.

    We pass defaults as-is, without any copies or default factories,
    so the rules of ``dataclasses`` and ``msgspec`` apply.
    """
    with pytest.raises((TypeError, ValueError), match='default'):

        class _Controller(Controller[serializer]):  # type: ignore[valid-type]
            def post(self, parsed_body: Body[Any] = default) -> str:
                raise NotImplementedError


def _build_union_controller(
    serializer: type[BaseSerializer],
    model: Any,
) -> type[Controller]:  # type: ignore[type-arg]
    class _UnionController(Controller[serializer]):  # type: ignore[valid-type]
        def post(
            self,
            parsed_body: Body[model | list[str] | int] = 0,  # pyright: ignore[reportInvalidTypeForm]
            parsed_query: Query[model | Literal['']] = '',  # pyright: ignore[reportInvalidTypeForm]
            parsed_cookies: Cookies[model | tuple[int, ...]] = (1, 2),  # pyright: ignore[reportInvalidTypeForm]
        ) -> dict[str, Any]:
            return {
                'body': parsed_body,
                'query': parsed_query,
                'cookies': parsed_cookies,
            }

    return _UnionController


@pytest.mark.parametrize(
    ('serializer', 'model'),
    list(zip(serializers, models, strict=True)),
)
@pytest.mark.parametrize(
    ('request_kwargs', 'expected'),
    [
        ({}, {'body': 0, 'query': '', 'cookies': [1, 2]}),
        (
            {'data': b'{"name": "body"}', 'content_type': _JSON},
            {'body': {'name': 'body'}, 'query': '', 'cookies': [1, 2]},
        ),
        (
            {'data': b'["list"]', 'content_type': _JSON},
            {'body': ['list'], 'query': '', 'cookies': [1, 2]},
        ),
        (
            {'data': b'5', 'content_type': _JSON},
            {'body': 5, 'query': '', 'cookies': [1, 2]},
        ),
    ],
)
def test_union_defaults(
    dmr_rf: DMRRequestFactory,
    serializer: type[BaseSerializer],
    model: Any,
    request_kwargs: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """Ensures that unions with defaults of other member types work."""
    request = dmr_rf.post('/whatever/', **request_kwargs)

    response = _build_union_controller(serializer, model).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == expected


@pytest.mark.parametrize(
    ('serializer', 'model'),
    list(zip(serializers, models, strict=True)),
)
def test_union_defaults_with_data(
    dmr_rf: DMRRequestFactory,
    serializer: type[BaseSerializer],
    model: Any,
) -> None:
    """Ensures that unions with defaults still parse provided data."""
    request = dmr_rf.post('/whatever/?name=query')
    request.COOKIES = {'name': 'cookies'}

    response = _build_union_controller(serializer, model).as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == {
        'body': 0,
        'query': {'name': 'query'},
        'cookies': {'name': 'cookies'},
    }


@final
class _AsyncController(Controller[PydanticSerializer]):
    async def post(self, parsed_body: Body[_Model | None] = None) -> str:
        return 'default' if parsed_body is None else parsed_body['name']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('request_kwargs', 'expected'),
    [
        ({}, 'default'),
        ({'data': b'{"name": "json"}', 'content_type': _JSON}, 'json'),
    ],
)
async def test_async_body_default(
    dmr_async_rf: DMRAsyncRequestFactory,
    request_kwargs: dict[str, Any],
    expected: str,
) -> None:
    """Ensures that async endpoints support defaults as well."""
    request = dmr_async_rf.post('/whatever/', **request_kwargs)

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == expected


@final
class _FilesController(Controller[PydanticSerializer]):
    parsers = (JsonParser(), MultiPartParser())

    def post(
        self,
        parsed_file_metadata: FileMetadata[_FileModel | None] = None,
    ) -> str:
        return (
            'default'
            if parsed_file_metadata is None
            else parsed_file_metadata['rules']['name']
        )


@pytest.mark.parametrize(
    ('request_kwargs', 'expected'),
    [
        ({}, 'default'),
        ({'data': {}, 'content_type': MULTIPART_CONTENT}, 'default'),
        ({'data': b'{}', 'content_type': _JSON}, 'default'),
        (
            {
                'data': {'rules': SimpleUploadedFile('rules.txt', b'abc')},
                'content_type': MULTIPART_CONTENT,
            },
            'rules.txt',
        ),
    ],
)
def test_file_metadata_default(
    dmr_rf: DMRRequestFactory,
    request_kwargs: dict[str, Any],
    expected: str,
) -> None:
    """Ensures that file metadata uses defaults when no files are sent."""
    request = dmr_rf.post('/whatever/', **request_kwargs)

    response = _FilesController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == expected


class _XmlModel(TypedDict):
    root: dict[str, str]


@final
class _ConditionalController(Controller[PydanticSerializer]):
    parsers = (JsonParser(), XmlParser())

    def post(
        self,
        parsed_body: Body[
            Annotated[
                _Model | _XmlModel | None,
                conditional_type({
                    ContentType.json: _Model | None,
                    'application/xml': _XmlModel,
                }),
            ]
        ] = None,
    ) -> str:
        return json.dumps(parsed_body)


@pytest.mark.parametrize(
    ('request_kwargs', 'expected'),
    [
        ({}, None),
        (
            {'data': b'{"name": "json"}', 'content_type': _JSON},
            {'name': 'json'},
        ),
        (
            {
                'data': b'<root><name>xml</name></root>',
                'content_type': 'application/xml',
            },
            {'root': {'name': 'xml'}},
        ),
    ],
)
def test_conditional_body_default(
    dmr_rf: DMRRequestFactory,
    request_kwargs: dict[str, Any],
    expected: dict[str, Any] | None,
) -> None:
    """Ensures that conditional models keep their defaults."""
    request = dmr_rf.post('/whatever/', **request_kwargs)

    response = _ConditionalController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(json.loads(response.content)) == expected


@final
class _AlwaysComponent(ComponentParser):
    """Component that ignores the default value."""

    context_name = 'parsed_always'

    @override
    def provide_context_data(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        *,
        field_model: Any,
        default: Any = EMPTY,
    ) -> dict[str, str]:
        return {'name': 'always'}

    @override
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: Any,
        controller_cls: type[Controller[BaseSerializer]],
        context: Any,
    ) -> Any:
        raise NotImplementedError


_Always: TypeAlias = Annotated[_Model | None, _AlwaysComponent()]


@final
class _CustomComponentController(Controller[PydanticSerializer]):
    def get(self, parsed_always: _Always = None) -> str:
        return 'default' if parsed_always is None else parsed_always['name']


def test_custom_component_ignores_default(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that custom components decide how to use defaults."""
    request = dmr_rf.get('/whatever/')

    response = _CustomComponentController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'always'
