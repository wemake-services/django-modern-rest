import json
from http import HTTPStatus
from typing import ClassVar, final

import pydantic
from django.http import HttpResponse
from faker import Faker

from django_modern_rest import (
    Controller,
    Query,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _ForceListQuery(pydantic.BaseModel):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('query',))
    query: list[str]
    regular: str


@final
class _QueryListController(
    Controller[PydanticSerializer],
    Query[_ForceListQuery],
):
    def get(self) -> str:
        return ' '.join([self.parsed_query.regular, *self.parsed_query.query])


def test_force_list_multiple(
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


@final
class _ForceListAllowEmpty(pydantic.BaseModel):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(('query',))
    query: list[str] = pydantic.Field(default_factory=list)
    regular: str


@final
class _QueryListEmptyController(
    Controller[PydanticSerializer],
    Query[_ForceListAllowEmpty],
):
    def get(self) -> str:
        return ' '.join([self.parsed_query.regular, *self.parsed_query.query])


def test_force_list_zero(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that query can have ``__drm_force_list__`` attr."""
    regular = faker.name()
    request = dmr_rf.get(
        f'/whatever/?regular={regular}',
    )

    response = _QueryListEmptyController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == regular


@final
class _TrimQuery(pydantic.BaseModel):
    query: str


@final
class _TrimQueryController(
    Controller[PydanticSerializer],
    Query[_TrimQuery],
):
    def get(self) -> str:
        return self.parsed_query.query


def test_trim_query(
    dmr_rf: DMRRequestFactory,
    faker: Faker,
) -> None:
    """Ensures that query can trim several values into a single one."""
    first_name = faker.name()
    last_name = faker.last_name()
    request = dmr_rf.get(
        f'/whatever/?query={first_name}&query={last_name}',
    )

    response = _TrimQueryController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers == {'Content-Type': 'application/json'}
    # Last passed value wins:
    assert json.loads(response.content) == last_name
