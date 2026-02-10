"""Unit tests for pagination functionality."""

import json
from http import HTTPStatus
from typing import Final, NotRequired, final

import pydantic
import pytest
from django.core.paginator import Paginator
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from django_modern_rest import Controller, Query
from django_modern_rest.pagination import Page, Paginated
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _User(pydantic.BaseModel):
    """Sample user model for testing."""

    email: str


class _PageQuery(TypedDict):
    """Query parameters for pagination."""

    page_size: NotRequired[int]
    page: NotRequired[int]


_USERS: Final = (
    _User(email='one@example.com'),
    _User(email='two@example.com'),
    _User(email='three@example.com'),
    _User(email='four@example.com'),
    _User(email='five@example.com'),
)


@final
class _PaginatedUsersController(
    Controller[PydanticSerializer],
    Query[_PageQuery],
):
    """Controller with pagination support."""

    def get(self) -> Paginated[_User]:
        """Return paginated list of users."""
        page = self.parsed_query.get('page', 1)
        page_size = self.parsed_query.get('page_size', 2)

        paginator = Paginator(_USERS, page_size)
        return Paginated(
            count=paginator.count,
            num_pages=paginator.num_pages,
            per_page=paginator.per_page,
            page=Page(
                number=page,
                object_list=list(paginator.page(page).object_list),
            ),
        )


@final
class _AsyncPaginatedUsersController(
    Controller[PydanticSerializer],
    Query[_PageQuery],
):
    """Async controller with pagination support."""

    async def get(self) -> Paginated[_User]:
        """Return paginated list of users."""
        page = self.parsed_query.get('page', 1)
        page_size = self.parsed_query.get('page_size', 2)

        paginator = Paginator(_USERS, page_size)
        return Paginated(
            count=paginator.count,
            num_pages=paginator.num_pages,
            per_page=paginator.per_page,
            page=Page(
                number=page,
                object_list=list(paginator.page(page).object_list),
            ),
        )


def test_pagination_basic(dmr_rf: DMRRequestFactory) -> None:
    """Test basic pagination returns correct structure."""
    request = dmr_rf.get('/users/')

    response = _PaginatedUsersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 5,
        'num_pages': 3,
        'per_page': 2,
        'page': {
            'number': 1,
            'object_list': [
                {'email': 'one@example.com'},
                {'email': 'two@example.com'},
            ],
        },
    })


def test_pagination_second_page(dmr_rf: DMRRequestFactory) -> None:
    """Test retrieving second page returns correct data."""
    request = dmr_rf.get('/users/', {'page': 2})

    response = _PaginatedUsersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 5,
        'num_pages': 3,
        'per_page': 2,
        'page': {
            'number': 2,
            'object_list': [
                {'email': 'three@example.com'},
                {'email': 'four@example.com'},
            ],
        },
    })


def test_pagination_last_page_partial(dmr_rf: DMRRequestFactory) -> None:
    """Test last page with partial results."""
    request = dmr_rf.get('/users/', {'page': 3})

    response = _PaginatedUsersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 5,
        'num_pages': 3,
        'per_page': 2,
        'page': {'number': 3, 'object_list': [{'email': 'five@example.com'}]},
    })


def test_pagination_custom_page_size(dmr_rf: DMRRequestFactory) -> None:
    """Test pagination with custom page size."""
    request = dmr_rf.get('/users/', {'page_size': 3})

    response = _PaginatedUsersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 5,
        'num_pages': 2,
        'per_page': 3,
        'page': {
            'number': 1,
            'object_list': [
                {'email': 'one@example.com'},
                {'email': 'two@example.com'},
                {'email': 'three@example.com'},
            ],
        },
    })


def test_pagination_single_item_per_page(dmr_rf: DMRRequestFactory) -> None:
    """Test pagination with one item per page."""
    request = dmr_rf.get('/users/', {'page_size': 1, 'page': 3})

    response = _PaginatedUsersController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 5,
        'num_pages': 5,
        'per_page': 1,
        'page': {'number': 3, 'object_list': [{'email': 'three@example.com'}]},
    })


@pytest.mark.asyncio
async def test_pagination_async(dmr_async_rf: DMRAsyncRequestFactory) -> None:
    """Test async pagination works correctly."""
    request = dmr_async_rf.get('/users/')

    response = await dmr_async_rf.wrap(
        _AsyncPaginatedUsersController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 5,
        'num_pages': 3,
        'per_page': 2,
        'page': {
            'number': 1,
            'object_list': [
                {'email': 'one@example.com'},
                {'email': 'two@example.com'},
            ],
        },
    })


@final
class _EmptyPaginatedController(Controller[PydanticSerializer]):
    """Controller with empty pagination."""

    def get(self) -> Paginated[_User]:
        """Return empty paginated list."""
        paginator: Paginator[_User] = Paginator([], 10)
        return Paginated(
            count=paginator.count,
            num_pages=paginator.num_pages,
            per_page=paginator.per_page,
            page=Page(
                number=1,
                object_list=list(paginator.page(1).object_list),
            ),
        )


def test_pagination_empty_dataset(dmr_rf: DMRRequestFactory) -> None:
    """Test pagination with empty dataset."""
    request = dmr_rf.get('/users/')

    response = _EmptyPaginatedController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 0,
        'num_pages': 1,
        'per_page': 10,
        'page': {'number': 1, 'object_list': []},
    })
