import json
from http import HTTPStatus
from typing import final

import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from django.http import HttpResponse
from faker import Faker

from dmr import (
    Controller,
    Headers,
    Query,
)
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.test import DMRRequestFactory


@final
class _HeadersModel(msgspec.Struct):
    first_name: str


@final
class _QueryModel(msgspec.Struct):
    last_name: str


@final
class _ComponentController(Controller[MsgspecSerializer]):
    def get(
        self,
        parsed_headers: Headers[_HeadersModel],
        parsed_query: Query[_QueryModel],
    ) -> str:
        first_name = parsed_headers.first_name
        last_name = parsed_query.last_name
        return f'{first_name} {last_name}'


def test_msgspec_components(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that regular parsing works."""
    first_name = faker.name()
    last_name = faker.last_name()
    request = dmr_rf.get(
        f'/whatever/?last_name={last_name}',
        data={},
        headers={'first_name': first_name},
    )

    response = _ComponentController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == f'{first_name} {last_name}'
