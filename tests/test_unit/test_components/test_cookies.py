import json
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse
from django.test import RequestFactory
from faker import Faker
from inline_snapshot import snapshot

from dmr import Controller, Cookies
from dmr.plugins.pydantic import PydanticSerializer


@final
class _CookieModel(pydantic.BaseModel):
    session_id: str
    user_id: int


@final
class _WrongPydanticBodyController(
    Controller[PydanticSerializer],
    Cookies[_CookieModel],
):
    def post(self) -> _CookieModel:
        return self.parsed_cookies


def test_cookie_parsing_correct(
    rf: RequestFactory,
    faker: Faker,
) -> None:
    """Ensures that correct cookies can be parsed."""
    endpoint = _WrongPydanticBodyController.api_endpoints['POST']
    assert endpoint.metadata.component_parsers == [
        (Cookies[_CookieModel], (_CookieModel,)),
    ]

    request = rf.post('/whatever/')
    request.COOKIES = {
        'session_id': faker.name(),
        'user_id': str(faker.pyint()),
    }

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert json.loads(response.content) == {
        'session_id': request.COOKIES['session_id'],
        'user_id': int(request.COOKIES['user_id']),
    }


def test_cookie_parsing_error(
    rf: RequestFactory,
    faker: Faker,
) -> None:
    """Ensures that incorrect cookies will raise an error."""
    request = rf.post('/whatever/')
    request.COOKIES = {'user_id': faker.name()}

    response = _WrongPydanticBodyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': 'Field required',
                'loc': ['parsed_cookies', 'session_id'],
                'type': 'value_error',
            },
            {
                'msg': (
                    'Input should be a valid integer, '
                    'unable to parse string as an integer'
                ),
                'loc': ['parsed_cookies', 'user_id'],
                'type': 'value_error',
            },
        ],
    })
