"""Unit tests for pagination functionality."""

import json
from http import HTTPStatus
from typing import Final, NotRequired, TypedDict, final

import pydantic
import pytest
from django.core.paginator import Paginator
from django.http import HttpResponse
from inline_snapshot import snapshot

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
        'page': {
            'number': 3,
            'object_list': [
                {'email': 'five@example.com'},
            ],
        },
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
        'page': {
            'number': 3,
            'object_list': [
                {'email': 'three@example.com'},
            ],
        },
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
        'page': {
            'number': 1,
            'object_list': [
                {'email': 'one@example.com'},
                {'email': 'two@example.com'},
            ],
        },
    })


@pytest.mark.asyncio
async def test_pagination_async_second_page(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Test async pagination second page."""
    request = dmr_async_rf.get('/users/', {'page': 2, 'page_size': 2})

    response = await dmr_async_rf.wrap(
        _AsyncPaginatedUsersController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 5,
        'num_pages': 3,
        'page': {
            'number': 2,
            'object_list': [
                {'email': 'three@example.com'},
                {'email': 'four@example.com'},
            ],
        },
    })


@final
class _EmptyPaginatedController(Controller[PydanticSerializer]):
    """Controller with empty pagination."""

    def get(self) -> Paginated[_User]:
        """Return empty paginated list."""
        paginator: Paginator[_User] = Paginator([], 10)
        # Django's Paginator.page(1) works for empty lists
        return Paginated(
            count=paginator.count,
            num_pages=paginator.num_pages,
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

    # Compute expected num_pages from Django's Paginator to avoid
    # coupling to specific Django version behavior
    expected_num_pages = Paginator([], 10).num_pages
    response_data = json.loads(response.content)
    assert response_data['count'] == 0
    assert response_data['num_pages'] == expected_num_pages
    assert response_data['page']['number'] == 1
    assert response_data['page']['object_list'] == []


@final
class _SimplePaginatedController(Controller[PydanticSerializer]):
    """Controller with simple string pagination."""

    def get(self) -> Paginated[str]:
        """Return paginated list of strings."""
        letters = ['a', 'b', 'c', 'd', 'e']
        paginator: Paginator[str] = Paginator(letters, 2)
        return Paginated(
            count=paginator.count,
            num_pages=paginator.num_pages,
            page=Page(
                number=1,
                object_list=list(paginator.page(1).object_list),
            ),
        )


def test_pagination_with_simple_types(dmr_rf: DMRRequestFactory) -> None:
    """Test pagination works with simple types like strings."""
    request = dmr_rf.get('/items/')

    response = _SimplePaginatedController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot({
        'count': 5,
        'num_pages': 3,
        'page': {
            'number': 1,
            'object_list': ['a', 'b'],
        },
    })


def test_page_dataclass_structure() -> None:
    """Test Page dataclass has correct structure."""
    page: Page[str] = Page(number=1, object_list=['a', 'b'])

    assert page.number == 1
    assert page.object_list == ['a', 'b']


def test_paginated_dataclass_structure() -> None:
    """Test Paginated dataclass has correct structure."""
    page: Page[str] = Page(number=1, object_list=['a', 'b'])
    paginated: Paginated[str] = Paginated(
        count=10,
        num_pages=5,
        page=page,
    )

    assert paginated.count == 10
    assert paginated.num_pages == 5
    assert paginated.page.number == 1
    assert paginated.page.object_list == ['a', 'b']


def test_page_dataclass_frozen() -> None:
    """Test Page dataclass is immutable."""
    page: Page[str] = Page(number=1, object_list=['a', 'b'])

    with pytest.raises(AttributeError):
        page.number = 2  # type: ignore[misc]


def test_paginated_dataclass_frozen() -> None:
    """Test Paginated dataclass is immutable."""
    page: Page[str] = Page(number=1, object_list=['a', 'b'])
    paginated: Paginated[str] = Paginated(
        count=10,
        num_pages=5,
        page=page,
    )

    with pytest.raises(AttributeError):
        paginated.count = 20  # type: ignore[misc]
