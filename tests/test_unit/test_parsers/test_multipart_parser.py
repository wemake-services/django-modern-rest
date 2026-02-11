import json
from http import HTTPStatus

import pydantic
from django.http import HttpResponse
from django.test import RequestFactory
from faker import Faker
from inline_snapshot import snapshot

from django_modern_rest import Body, Controller
from django_modern_rest.parsers import MultiPartParser
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _User(pydantic.BaseModel):
    username: str
    age: int


class _UserController(Controller[PydanticSerializer], Body[_User]):
    parsers = (MultiPartParser(),)

    def post(self) -> _User:
        return self.parsed_body


def test_multipart_correct_request(
    rf: RequestFactory,
    faker: Faker,
) -> None:
    """Ensures we can send empty bytes to our json parser."""
    request_data = {'username': faker.name(), 'age': faker.pyint()}
    request = rf.post(
        '/whatever/',
        data=request_data,
    )

    response = _UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == request_data


def test_multipart_empty_request(
    rf: RequestFactory,
    faker: Faker,
) -> None:
    """Ensures we can send empty bytes to our json parser."""
    request = rf.post(
        '/whatever/',
        data={},
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
                'msg': 'Field required',
                'loc': ['parsed_body', 'age'],
                'type': 'value_error',
            },
        ],
    })
