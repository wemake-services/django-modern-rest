import json
from http import HTTPStatus
from typing import ClassVar, final

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
class _ComponentController(
    Controller[MsgspecSerializer],
    Headers[_HeadersModel],
    Query[_QueryModel],
):
    def get(self) -> str:
        first_name = self.parsed_headers.first_name
        last_name = self.parsed_query.last_name
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


@final
class _ForceListQuery(msgspec.Struct):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('query',))

    query: list[str]
    regular: str


@final
class _QueryListController(
    Controller[MsgspecSerializer],
    Query[_ForceListQuery],
):
    def get(self) -> str:
        return ' '.join([self.parsed_query.regular, *self.parsed_query.query])


def test_msgspec_force_list_query(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that query can have ``__drm_force_list__`` attr."""
    first_name = faker.name()
    last_name = faker.last_name()
    regular = faker.name()
    request = dmr_rf.get(
        f'/whatever/?query={first_name}&query={last_name}&regular={regular}',
    )

    response = _QueryListController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == f'{regular} {first_name} {last_name}'
