import pytest
from django.db import models

from dmr.pagination.cursor import CursorPaginator, InvalidCursorError
from server.apps.model_cursor.models import (  # type: ignore[import-not-found]
    Entry,
)


def _encode(paginator: CursorPaginator[Entry], *to_encode: str) -> str:
    """Encode cursor values with the default encoder."""
    return paginator._cursor_encoder(paginator._separator.join(to_encode))


@pytest.mark.parametrize('per_page', [0, -1])
def test_invalid_per_page_raises_value_error(per_page: int) -> None:
    """`per_page` must be a positive integer."""
    with pytest.raises(ValueError, match='per_page'):
        CursorPaginator(
            Entry.objects.none().order_by('rank'),
            per_page=per_page,
        )


@pytest.mark.parametrize(
    'cursor',
    [
        pytest.param('abc', id='invalid-base64'),
        pytest.param('////', id='invalid-utf-8'),
    ],
)
def test_undecodable_cursor_raises(cursor: str) -> None:
    """Cursors that cannot be decoded are rejected."""
    paginator = CursorPaginator(
        Entry.objects.none().order_by('rank'),
        per_page=2,
    )
    with pytest.raises(InvalidCursorError, match='cannot be decoded'):
        paginator.page(cursor)


def test_cursor_with_wrong_field_count_raises() -> None:
    """A cursor must contain one value per ordered field."""
    paginator = CursorPaginator(
        Entry.objects.none().order_by('rank', 'name'),
        per_page=2,
    )
    with pytest.raises(
        InvalidCursorError,
        match='Cursor has 2 fields, but 3 were expected',
    ):
        paginator.page(_encode(paginator, '1', 'c'))


def test_empty_result_page() -> None:
    """An empty queryset yields an empty page without a next cursor."""
    paginator = CursorPaginator(
        Entry.objects.none().order_by('rank'),
        per_page=2,
    )
    page = paginator.page()
    assert page.objects_list == []
    assert page.next_cursor is None


async def test_empty_result_page_async() -> None:
    """Async version of :func:`test_empty_result_page`."""
    paginator = CursorPaginator(
        Entry.objects.none().order_by('rank'),
        per_page=2,
    )
    page = await paginator.apage()
    assert page.objects_list == []
    assert page.next_cursor is None


def test_complex_order_by() -> None:
    """Test that plain strings are forced in order_by."""
    with pytest.raises(TypeError):
        CursorPaginator(
            Entry.objects.none().order_by(models.F('rank')),
            per_page=10,
        )
