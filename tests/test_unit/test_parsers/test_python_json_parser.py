import json
from http import HTTPStatus

import pydantic
import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest import (
    Body,
    Controller,
)
from django_modern_rest.parsers import JsonParser
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.renderers import JsonRenderer
from django_modern_rest.settings import Settings
from django_modern_rest.test import DMRRequestFactory


@pytest.fixture(autouse=True)
def _clear_parser_and_renderer(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.parsers: [JsonParser],
        Settings.renderers: [JsonRenderer],
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


def test_empty_request_data(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures we can send empty bytes to our json parser."""

    class _Controller(Controller[PydanticSerializer], Body[None]):
        def post(self) -> str:
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
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
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

    class _Controller(Controller[PydanticSerializer], Body[None]):
        def post(self) -> str:
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
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Expecting property name enclosed in double quotes: '
                    'line 1 column 2 (char 1)'
                ),
                'type': 'value_error',
            },
        ],
    })


class _UserModel(pydantic.BaseModel):
    username: str


class _RequestModel(pydantic.BaseModel):
    user: _UserModel


def test_complex_request_data(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures we can change per-endpoint parsers and renderers."""

    class _Controller(Controller[PydanticSerializer], Body[_RequestModel]):
        def post(self) -> _RequestModel:
            return self.parsed_body

    assert len(_Controller.api_endpoints['POST'].metadata.parsers) == 1
    assert len(_Controller.api_endpoints['POST'].metadata.renderers) == 1

    request_data = {'user': {'username': faker.name()}}

    request = dmr_rf.post(
        '/whatever/',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        data=json.dumps(request_data),
    )

    response = _Controller.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == request_data
