import dataclasses
import json
import uuid
from http import HTTPStatus
from typing import Annotated, Any, TypeAlias, final

import pydantic
import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from pydantic.functional_serializers import PlainSerializer
from pydantic_extra_types import Color

from dmr import Controller, Query
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.test import DMRRequestFactory

FancyInt: TypeAlias = Annotated[
    int,
    PlainSerializer(
        lambda to_dump: f'{to_dump:,}',
        return_type=str,
        when_used='json',
    ),
]


@final
@dataclasses.dataclass
class _QueryModel:
    query: pydantic.EmailStr
    number: int
    color: Color
    uid: uuid.UUID
    email: pydantic.NameEmail
    tag: FancyInt


@final
@pydantic.dataclasses.dataclass
class _QueryPydanticModel:
    query: pydantic.EmailStr
    number: int
    color: Color
    uid: uuid.UUID
    email: pydantic.NameEmail
    tag: FancyInt


@pytest.mark.parametrize(
    'model',
    [
        _QueryModel,
        _QueryPydanticModel,
    ],
)
def test_pydantic_dataclasses_work(
    dmr_rf: DMRRequestFactory,
    *,
    model: type[Any],
) -> None:
    """Ensures that correct dataclasses and pydantic work."""

    class _RawController(Controller[PydanticSerializer]):
        renderers = (JsonRenderer(),)
        parsers = (JsonParser(),)

        def get(self, parsed_query: Query[model]) -> model:  # type: ignore[valid-type]
            return parsed_query

    uid = str(uuid.uuid4())
    name_email = 'Some User <some.user@example.com>'
    request = dmr_rf.get(
        '/whatever/?query=a@example.com&number=1&'
        f'color=black&uid={uid}&email={name_email}&'
        'tag=1234',
    )

    response = _RawController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        'query': 'a@example.com',
        'number': 1,
        'color': 'black',
        'uid': uid,
        'email': name_email,
        'tag': '1,234',
    }


@pytest.mark.parametrize(
    'model',
    [
        _QueryModel,
        _QueryPydanticModel,
    ],
)
def test_pydantic_dataclasses_validates(
    dmr_rf: DMRRequestFactory,
    *,
    model: type[Any],
) -> None:
    """Ensures that pydantic validation works for dataclasses."""

    class _RawController(Controller[PydanticSerializer]):
        renderers = (JsonRenderer(),)
        parsers = (JsonParser(),)

        def get(self, parsed_query: Query[model]) -> model:  # type: ignore[valid-type]
            raise NotImplementedError

    request = dmr_rf.get(
        '/whatever/?query=a&number=b&color=wrong',
    )

    response = _RawController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'value is not a valid email address: '
                    'An email address must have an @-sign.'
                ),
                'loc': ['parsed_query', 'query'],
                'type': 'value_error',
            },
            {
                'msg': (
                    'Input should be a valid integer, '
                    'unable to parse string as an integer'
                ),
                'loc': ['parsed_query', 'number'],
                'type': 'value_error',
            },
            {
                'msg': (
                    'value is not a valid color: string not '
                    'recognised as a valid color'
                ),
                'loc': ['parsed_query', 'color'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_query', 'uid'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_query', 'email'],
                'type': 'value_error',
            },
            {
                'msg': 'Field required',
                'loc': ['parsed_query', 'tag'],
                'type': 'value_error',
            },
        ],
    })
