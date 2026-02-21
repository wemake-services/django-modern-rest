import json
from http import HTTPStatus
from typing import ClassVar, final

import pydantic
import pytest
from django.http import HttpResponse
from faker import Faker

from dmr import (
    Controller,
    Query,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


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


@final
class _DefaultCastNullQuery(pydantic.BaseModel):
    query: str


@final
class _EnableCastNullQuery(pydantic.BaseModel):
    __dmr_cast_null__: ClassVar[bool] = True
    query: str | None


@final
class _DefaultCastNullController(
    Controller[PydanticSerializer],
    Query[_DefaultCastNullQuery],
):
    def get(self) -> _DefaultCastNullQuery:
        return self.parsed_query


@final
class _EnableCastNullController(
    Controller[PydanticSerializer],
    Query[_EnableCastNullQuery],
):
    def get(self) -> _EnableCastNullQuery:
        return self.parsed_query


@pytest.mark.parametrize(
    ('controller_cls', 'expected_query_value'),
    [
        (_DefaultCastNullController, 'null'),
        (_EnableCastNullController, None),
    ],
)
def test_default_cast_null(
    dmr_rf: DMRRequestFactory,
    *,
    controller_cls: Controller[PydanticSerializer],
    expected_query_value: str | None,
) -> None:
    """Ensures that query casts 'null' to None or not."""
    request = dmr_rf.get('/whatever/?query=null')
    response = controller_cls.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'query': expected_query_value}
