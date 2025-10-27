import json
from http import HTTPStatus
from typing import Annotated, final

import pytest

try:
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from django.http import HttpResponse
from faker import Faker

from django_modern_rest import (
    Controller,
    Headers,
    Query,
)
from django_modern_rest.plugins.msgspec import MsgspecSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _HeadersModel(msgspec.Struct):
    first_name: str


@final
class _QueryModel(msgspec.Struct):
    # queries are always lists:
    last_name: Annotated[list[str], msgspec.Meta(min_length=1, max_length=1)]


@final
class _ComponentController(
    Controller[MsgspecSerializer],
    Headers[_HeadersModel],
    Query[_QueryModel],
):
    def get(self) -> str:
        first_name = self.parsed_headers.first_name
        last_name = self.parsed_query.last_name[0]
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
