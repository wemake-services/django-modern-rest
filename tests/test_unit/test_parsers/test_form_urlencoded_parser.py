import json
from http import HTTPMethod, HTTPStatus
from urllib.parse import urlencode

import pydantic
import pytest
from django.http import HttpResponse
from faker import Faker
from inline_snapshot import snapshot

from dmr import Body, Controller, modify
from dmr.negotiation import ContentType
from dmr.parsers import FormUrlEncodedParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


class _User(pydantic.BaseModel):
    username: str
    age: int


class _UserController(Controller[PydanticSerializer], Body[_User]):
    parsers = (FormUrlEncodedParser(),)

    @modify(status_code=HTTPStatus.OK)
    def post(self) -> _User:
        return self.parsed_body

    def put(self) -> _User:
        return self.parsed_body

    def patch(self) -> _User:
        return self.parsed_body


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
    ],
)
def test_form_correct_request(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures we can send valid data to our form."""
    request_data = {'username': faker.name(), 'age': faker.pyint()}
    request = dmr_rf.generic(
        str(method),
        '/whatever/',
        data=urlencode(request_data),
        headers={'Content-Type': str(ContentType.x_www_form_urlencoded)},
    )

    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == request_data


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
    ],
)
def test_form_wrong_request(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures we can send invalid data to our form."""
    request_data = {'age': faker.name()}
    request = dmr_rf.generic(
        str(method),
        '/whatever/',
        data=urlencode(request_data),
        headers={'Content-Type': str(ContentType.x_www_form_urlencoded)},
    )

    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_body', 'username'],
                'type': 'value_error',
            },
            {
                'msg': (
                    'Input should be a valid integer, '
                    'unable to parse string as an integer'
                ),
                'loc': ['parsed_body', 'age'],
                'type': 'value_error',
            },
        ],
    })


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
    ],
)
def test_form_wrong_charset(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures we can send valid data to our form."""
    request_data = {'username': faker.name(), 'age': faker.pyint()}
    request = dmr_rf.generic(
        str(method),
        '/whatever/',
        data=urlencode(request_data),
        headers={
            'Content-Type': 'application/x-www-form-urlencoded; charset=latin',
        },
    )

    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'HTTP requests with the '
                    "'application/x-www-form-urlencoded' content type must "
                    'be UTF-8 encoded.'
                ),
                'type': 'value_error',
            },
        ],
    })
