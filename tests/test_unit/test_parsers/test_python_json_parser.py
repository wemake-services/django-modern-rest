import datetime as dt
import json
from http import HTTPMethod, HTTPStatus
from typing import Final

import pydantic
import pytest
from dirty_equals import IsDatetime
from django.conf import LazySettings
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from dmr import Body, Controller, ResponseSpec, validate
from dmr.internal.json import JsonModule, NativeJson
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory

_json_modules: Final[list[JsonModule]] = [NativeJson]

try:  # pragma: no cover
    import orjson  # type: ignore[import-not-found, unused-ignore]
except ImportError:  # pragma: no cover
    pass  # noqa: WPS420
else:  # pragma: no cover
    _json_modules.append(orjson)  # pyright: ignore[reportArgumentType]


@pytest.fixture(params=_json_modules)
def json_module(request: pytest.FixtureRequest) -> JsonModule:
    """Parametrize json modules."""
    return request.param  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _clear_parser_and_renderer(
    settings: LazySettings,
    json_module: JsonModule,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.parsers: [JsonParser(json_module=json_module)],
        Settings.renderers: [JsonRenderer(json_module=json_module)],
    }


def test_native_json_metadata() -> None:
    """Ensures that metadata is correct."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> str:
            raise NotImplementedError

    metadata = _Controller.api_endpoints['GET'].metadata
    assert metadata.responses.keys() == {
        HTTPStatus.OK,
        HTTPStatus.NOT_ACCEPTABLE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    }
    assert len(metadata.parsers) == 1
    assert len(metadata.renderers) == 1
    assert metadata.auth is None
    assert metadata.throttling_before_auth is None
    assert metadata.throttling_after_auth is None


@pytest.mark.parametrize(
    'request_headers',
    [
        {
            'Content-Type': 'application/json',
        },
        {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    ],
)
def test_empty_request_data(
    dmr_rf: DMRRequestFactory,
    *,
    request_headers: dict[str, str],
) -> None:
    """Ensures we can send empty bytes to our json parser."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[None]) -> str:
            return 'none handled'

    metadata = _Controller.api_endpoints['POST'].metadata
    assert metadata.responses.keys() == {
        HTTPStatus.CREATED,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.NOT_ACCEPTABLE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
    }
    assert len(metadata.parsers) == 1
    assert len(metadata.renderers) == 1

    request = dmr_rf.post(
        '/whatever/',
        headers=request_headers,
        data=b'',
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == 'none handled'


def test_wrong_request_data(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we can send wrong bytes to our json parser."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[None]) -> str:
            raise NotImplementedError

    assert len(_Controller.api_endpoints['POST'].metadata.parsers) == 1
    assert len(_Controller.api_endpoints['POST'].metadata.renderers) == 1

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        data=b'{><!$',
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content)['detail']


class _UserModel(pydantic.BaseModel):
    username: str
    tags: set[str]
    groups: frozenset[str]


class _RequestModel(pydantic.BaseModel):
    user: _UserModel


@pytest.mark.parametrize(
    'request_headers',
    [
        {},
        {
            'Content-Type': 'application/json',
        },
        {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    ],
)
def test_complex_request_data(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    request_headers: dict[str, str],
) -> None:
    """Ensures we that complex data can be in models."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[_RequestModel]) -> _RequestModel:
            return parsed_body

    assert len(_Controller.api_endpoints['POST'].metadata.parsers) == 1
    assert len(_Controller.api_endpoints['POST'].metadata.renderers) == 1

    request_data = {
        'user': {
            'username': faker.name(),
            'tags': [faker.unique.name(), faker.unique.name()],
            'groups': [faker.name()],
        },
    }

    request = dmr_rf.post(
        '/whatever/',
        headers=request_headers,
        data=json.dumps(request_data),
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}

    response_data = json.loads(response.content)
    # All this work to be sure that `set` field order is ignored:
    assert len(response_data) == 1
    assert len(response_data['user']) == len(request_data['user'])
    assert response_data['user']['username'] == request_data['user']['username']
    assert sorted(response_data['user']['tags']) == sorted(
        request_data['user']['tags'],
    )
    assert response_data['user']['groups'] == request_data['user']['groups']


def test_complex_direct_return_data(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that complex data can directly be returned."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[frozenset[str]]) -> frozenset[str]:
            return parsed_body

    assert len(_Controller.api_endpoints['POST'].metadata.parsers) == 1
    assert len(_Controller.api_endpoints['POST'].metadata.renderers) == 1

    request_data = [faker.unique.name(), faker.unique.name()]

    request = dmr_rf.post(
        '/whatever/',
        data=json.dumps(request_data),
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}

    assert sorted(json.loads(response.content)) == sorted(request_data)


def test_json_parser_validation(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures orjson can handle complex pydantic model data."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[_UserModel]) -> _UserModel:
            raise NotImplementedError

    request_data = {'username': faker.name()}

    request = dmr_rf.post(
        '/whatever/',
        data=json.dumps(request_data),
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_body', 'tags'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_body', 'groups'],
                'type': 'value_error',
            },
        ],
    })


class _ProductModel(pydantic.BaseModel):
    product: str
    created_at: dt.datetime
    updated_at: dt.datetime


@pytest.mark.parametrize(
    'timezone',
    [
        dt.UTC,
        dt.timezone(offset=dt.timedelta(hours=3), name='MSK'),
        dt.timezone(offset=dt.timedelta(hours=7), name='NSK'),
        dt.timezone(offset=dt.timedelta(hours=-7), name='LA'),
    ],
)
@pytest.mark.parametrize('method', [HTTPMethod.GET, HTTPMethod.PUT])
def test_json_parser_return_validation(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    timezone: dt.timezone,
    method: HTTPMethod,
) -> None:
    """Ensures validation works for datetime fields with different timezones."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> _ProductModel:
            now = dt.datetime.now(timezone)
            return _ProductModel(
                product='product',
                created_at=now,
                updated_at=now,
            )

        @validate(ResponseSpec(_ProductModel, status_code=HTTPStatus.OK))
        def put(self) -> HttpResponse:
            # See https://github.com/wemake-services/django-modern-rest/issues/938
            return self.to_response(self.get())

    request = dmr_rf.generic(str(method), '/whatever/')

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == snapshot({
        'product': 'product',
        'created_at': IsDatetime(iso_string=True),
        'updated_at': IsDatetime(iso_string=True),
    })
