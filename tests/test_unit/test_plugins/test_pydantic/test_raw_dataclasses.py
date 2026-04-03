import dataclasses
import json
from http import HTTPStatus
from typing import final

from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller, Query
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.test import DMRRequestFactory


@final
@dataclasses.dataclass
class _QueryModel:
    query: str
    number: int


@final
class _RawController(Controller[PydanticSerializer]):
    renderers = (JsonRenderer(),)
    parsers = (JsonParser(),)

    def get(self, parsed_query: Query[_QueryModel]) -> _QueryModel:
        return parsed_query


def test_pydantic_dataclasses_work(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that correct dataclasses and pydantic work."""
    request = dmr_rf.get(
        '/whatever/?query=a&number=1',
    )

    response = _RawController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({'query': 'a', 'number': 1})


def test_pydantic_dataclasses_validates(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that pydantic validation works for dataclasses."""
    request = dmr_rf.get(
        '/whatever/?query=a&number=b',
    )

    response = _RawController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Input should be a valid integer, unable to '
                    'parse string as an integer'
                ),
                'loc': ['parsed_query', 'number'],
                'type': 'value_error',
            },
        ],
    })
