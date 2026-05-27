"""Unit tests for pagination functionality."""

import json
from http import HTTPStatus
from typing import Final, NotRequired, final

import pytest
from django.core.paginator import Paginator
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import TypedDict

from dmr.pagination import InvalidPaginationCursorError
from server.apps.model_simple import (  # type: ignore[import-not-found]
    models,
)

try:
    # These tests do not work with raw python renderer.
    import msgspec
except ImportError:  # pragma: no cover
    pytest.skip(reason='msgspec is not installed', allow_module_level=True)

from dmr import Controller, Query
from dmr.pagination import (
    DjangoCursorPaginator,
    Page,
    Paginated,
)
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@final
class _User(msgspec.Struct):
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
    Controller[MsgspecSerializer],
):
    """Controller with pagination support."""

    def get(self, parsed_query: Query[_PageQuery]) -> Paginated[_User]:
        """Return paginated list of users."""
        page = parsed_query.get('page', 1)
        page_size = parsed_query.get('page_size', 2)

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


@final
class _AsyncPaginatedUsersController(
    Controller[MsgspecSerializer],
):
    """Async controller with pagination support."""

    async def get(self, parsed_query: Query[_PageQuery]) -> Paginated[_User]:
        """Return paginated list of users."""
        page = parsed_query.get('page', 1)
        page_size = parsed_query.get('page_size', 2)

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
class _EmptyPaginatedController(Controller[MsgspecSerializer]):
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
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == snapshot({
        'count': 0,
        'num_pages': 1,
        'per_page': 10,
        'page': {'number': 1, 'object_list': []},
    })


@pytest.fixture
async def setup_users() -> None:
    """Fill database with test fields."""
    # only 1, 2 and 3 models will have non-null order fields
    users = [
        models.CursorPaginatedTestModel(order_field=idx)
        if idx > 2
        else models.CursorPaginatedTestModel()
        for idx in reversed(range(1, 11))
    ]
    await models.CursorPaginatedTestModel.objects.abulk_create(users)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_invalid_django_cursor_error() -> None:
    """Test raising of `InvalidPaginationCursorError`."""
    paginator = DjangoCursorPaginator(
        ('id',),
        models.CursorPaginatedTestModel.objects.all(),
    )

    # non ascii
    with pytest.raises(InvalidPaginationCursorError):
        paginator._decode_cursor('🥵')
    # invalid base64 length
    with pytest.raises(InvalidPaginationCursorError):
        paginator._decode_cursor('a')
    # invalid utf-8 bytes
    with pytest.raises(InvalidPaginationCursorError):
        paginator._decode_cursor('//8=')


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.usefixtures('setup_users')
async def test_django_paginator_move_forward() -> None:
    """Test getting of next pages with cursor paginator."""
    paginator = DjangoCursorPaginator(
        ('id',),
        models.CursorPaginatedTestModel.objects.all(),
    )

    page = await paginator.page(2)
    assert len(page.object_list) == 2
    assert [model.id for model in page.object_list] == [1, 2]
    assert page.next_cursor is not None

    page = await paginator.page(10, cursor=page.next_cursor)
    assert len(page.object_list) == 8
    assert [model.id for model in page.object_list] == [3, 4, 5, 6, 7, 8, 9, 10]
    assert page.next_cursor is None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.usefixtures('setup_users')
async def test_django_paginator_move_back() -> None:
    """Test getting of previous pages with cursor paginator."""
    paginator = DjangoCursorPaginator(
        ('id',),
        models.CursorPaginatedTestModel.objects.all(),
    )

    page = await paginator.page(2)
    assert len(page.object_list) == 2
    assert [model.id for model in page.object_list] == [1, 2]
    assert page.prev_cursor is None

    page = await paginator.page(3, cursor=page.next_cursor)
    assert len(page.object_list) == 3
    assert [model.id for model in page.object_list] == [3, 4, 5]
    assert page.prev_cursor is not None

    page = await paginator.prev_page(2, cursor=page.prev_cursor)
    assert len(page.object_list) == 2
    assert [model.id for model in page.object_list] == [2, 1]
    assert page.prev_cursor is None

    page = await paginator.page(3, cursor=page.next_cursor)
    assert len(page.object_list) == 3
    assert [model.id for model in page.object_list] == [3, 4, 5]
    assert page.prev_cursor is not None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.usefixtures('setup_users')
async def test_django_paginator_nullable_cursor_values() -> None:
    """Test pagination when cursor contains nullable field values."""
    paginator = DjangoCursorPaginator(
        ('order_field', 'id'),
        models.CursorPaginatedTestModel.objects.all(),
    )

    page = await paginator.page(4)
    assert len(page.object_list) == 4
    # non nullable values goes first
    assert [model.order_field for model in page.object_list] == [3, 4, 5, 6]
    assert page.next_cursor is not None

    page = await paginator.page(4, cursor=page.next_cursor)
    assert len(page.object_list) == 4
    # non nullable values goes first
    assert [model.order_field for model in page.object_list] == [7, 8, 9, 10]
    assert page.next_cursor is not None

    page = await paginator.page(2, cursor=page.next_cursor)
    assert len(page.object_list) == 2
    assert [model.order_field for model in page.object_list] == [None, None]
    assert page.prev_cursor is not None

    page = await paginator.prev_page(2, cursor=page.prev_cursor)
    assert [model.order_field for model in page.object_list] == [10, 9]

    page = await paginator.page(9)
    assert len(page.object_list) == 9
    assert [model.order_field for model in page.object_list] == [
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        None,
    ]
    assert page.next_cursor is not None

    assert paginator._decode_cursor(page.next_cursor) == (None, '9')
    page = await paginator.page(1, cursor=page.next_cursor)
    assert len(page.object_list) == 1
    assert [model.order_field for model in page.object_list] == [None]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True, reset_sequences=True)
async def test_empty_django_paginator() -> None:
    """Test pagination on an empty queryset."""
    paginator = DjangoCursorPaginator(
        ('id',),
        models.CursorPaginatedTestModel.objects.all(),
    )

    page = await paginator.page(10)
    assert len(page.object_list) == 0
    assert page.next_cursor is None
    assert page.prev_cursor is None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.usefixtures('setup_users')
async def test_django_paginator_reverse_order() -> None:
    """Test getting of next and previous pages with reversed ordering."""
    paginator = DjangoCursorPaginator(
        ('-id',),
        models.CursorPaginatedTestModel.objects.all(),
    )

    page = await paginator.page(2)
    assert len(page.object_list) == 2
    assert [model.id for model in page.object_list] == [10, 9]
    assert page.next_cursor is not None

    page = await paginator.page(3, cursor=page.next_cursor)
    assert len(page.object_list) == 3
    assert [model.id for model in page.object_list] == [8, 7, 6]
    assert page.prev_cursor is not None

    page = await paginator.prev_page(2, cursor=page.prev_cursor)
    assert len(page.object_list) == 2
    assert [model.id for model in page.object_list] == [9, 10]

    page = await paginator.page(5)
    assert len(page.object_list) == 5
    # null-values goes first
    assert [model.order_field for model in page.object_list] == [
        None,
        None,
        3,
        4,
        5,
    ]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_position_from_instance_breaks_on_none() -> None:
    """Test nested attribute traversal stops on ``None``."""
    paginator = DjangoCursorPaginator(
        ('order_field__id',),
        models.CursorPaginatedTestModel.objects.none(),
    )

    position = paginator._position_from_instance(
        models.CursorPaginatedTestModel(),
    )

    assert position == [None]
