import json
from http import HTTPStatus

import orjson
import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from faker import Faker

from dmr import Body, Controller
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory


@pytest.fixture(autouse=True)
def _clear_parser_and_renderer(
    settings: LazySettings,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.parsers: [JsonParser(json_module=orjson)],
        Settings.renderers: [JsonRenderer(json_module=orjson)],
    }


def test_orjson_parser_parses_valid_json(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures orjson can parse valid JSON request bodies."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[dict[str, str]]) -> dict[str, str]:
            return parsed_body

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        data=orjson.dumps({'key': 'value'}),
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == {'key': 'value'}


def test_orjson_parser_empty_body(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures orjson parser handles empty body gracefully."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[None]) -> str:
            return 'none handled'

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        data=b'',
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == 'none handled'


def test_orjson_parser_invalid_json(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures orjson parser raises DataParsingError on invalid JSON."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[None]) -> str:
            raise NotImplementedError

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


class _UserModel(pydantic.BaseModel):
    username: str
    age: int


def test_orjson_parser_complex_data(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures orjson can handle complex pydantic model data."""

    class _Controller(Controller[PydanticSerializer]):
        def post(self, parsed_body: Body[_UserModel]) -> _UserModel:
            return parsed_body

    request_data = {'username': faker.name(), 'age': 25}

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        data=orjson.dumps(request_data),
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert json.loads(response.content) == request_data


def test_orjson_renderer_returns_bytes(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that the orjson renderer produces valid JSON bytes."""

    class _Controller(Controller[PydanticSerializer]):
        def get(self) -> dict[str, str]:
            return {'hello': 'world'}

    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Accept': 'application/json',
        },
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == {'hello': 'world'}
