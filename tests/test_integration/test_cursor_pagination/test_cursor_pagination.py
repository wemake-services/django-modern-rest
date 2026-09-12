import operator
from http import HTTPStatus
from typing import Any, Final

import pytest
from django.urls import reverse

from dmr.test import DMRAsyncClient, DMRClient
from server.apps.model_cursor.models import (  # type: ignore[import-not-found]
    Entry,
)

_SYNC_VIEW: Final = 'api:model_cursor:entries'
_ASYNC_VIEW: Final = 'api:model_cursor:entries_async'
_ORDER_BY_PARAMS: Final = (
    pytest.param(['rank', 'name'], id='rank+name'),
    pytest.param(['rank'], id='rank'),
    pytest.param(['-rank'], id='-rank'),
    pytest.param(['-rank', 'name'], id='-rank+name'),
    pytest.param(['name'], id='name'),
    pytest.param(['name', 'rank'], id='name+rank'),
    pytest.param(['created_at'], id='created_at'),
)
_LIMIT_PARAMS: Final = (1, 2, 3, 5, 10)

# ``(rank, name)`` pairs, created in this exact order.
# The ``name`` values are deliberately out of rank order so that
# different ``order_by`` fields produce different sequences:
_SEED_ENTRIES: Final = (
    (1, 'c'),
    (2, 'a'),
    (3, 'e'),
    (4, 'b'),
    (5, 'd'),
)


@pytest.fixture
def seeded_entries() -> list[Entry]:
    """Five entries with distinct ranks, names and creation order."""
    return [
        Entry.objects.create(rank=rank, name=name)
        for rank, name in _SEED_ENTRIES
    ]


def _expected_ranks(
    entries: list[Entry],
    order_by: list[str],
) -> list[int]:
    """Compute the rank sequence a given ``order_by`` should produce."""
    ordered = list(entries)
    for order in reversed(order_by):
        descending = order.startswith('-')
        field = order.removeprefix('-')
        ordered = sorted(
            ordered,
            key=operator.attrgetter(field),
            reverse=descending,
        )
    return [entry.rank for entry in ordered]


def _walk_pagination(
    client: DMRClient,
    url: str,
    query_params: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Walk every page of a cursor-paginated endpoint.

    Fires requests using the given ``query_params``, threading the
    ``next_cursor`` forward, until we don't have new pages.
    Returns all the page payloads in order.
    """
    request_params = dict(query_params)
    pages: list[dict[str, Any]] = []
    while True:
        response = client.get(url, request_params)
        assert response.status_code == HTTPStatus.OK, response.content
        data = response.json()
        pages.append(data)
        if data['next_cursor'] is None:
            return pages
        request_params['cursor'] = data['next_cursor']


async def _awalk_pagination(
    client: DMRAsyncClient,
    url: str,
    query_params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Async version of :func:`walk_pagination`."""
    request_params = dict(query_params)
    pages: list[dict[str, Any]] = []
    while True:
        response = await client.get(url, request_params)
        assert response.status_code == HTTPStatus.OK, response.content
        data = response.json()
        pages.append(data)
        if data['next_cursor'] is None:
            return pages
        request_params['cursor'] = data['next_cursor']


def _assert_walk(
    pages: list[dict[str, Any]],
    entries: list[Entry],
    order_by: list[str],
    limit: int,
) -> None:
    """Assert that a walk covers every entry, once, in order."""
    walked = [entry['rank'] for page in pages for entry in page['page']]
    assert walked == _expected_ranks(entries, order_by)
    for page in pages:
        assert page['per_page'] == limit
        assert len(page['page']) <= limit
    for page in pages[:-1]:
        assert len(page['page']) == limit


@pytest.mark.django_db
@pytest.mark.parametrize('view_name', [_SYNC_VIEW])
@pytest.mark.parametrize('order_by', _ORDER_BY_PARAMS)
@pytest.mark.parametrize('limit', _LIMIT_PARAMS)
def test_cursor_pagination_walk(
    dmr_client: DMRClient,
    seeded_entries: list[Entry],
    view_name: str,
    order_by: list[str],
    limit: int,
) -> None:
    """The sync endpoint walks every entry exactly once, in order."""
    pages = _walk_pagination(
        dmr_client,
        reverse(view_name),
        {'order_by': order_by, 'limit': limit},
    )
    _assert_walk(pages, seeded_entries, order_by, limit)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('view_name', [_ASYNC_VIEW])
@pytest.mark.parametrize('order_by', _ORDER_BY_PARAMS)
@pytest.mark.parametrize('limit', _LIMIT_PARAMS)
async def test_cursor_pagination_walk_async(
    dmr_async_client: DMRAsyncClient,
    seeded_entries: list[Entry],
    view_name: str,
    order_by: list[str],
    limit: int,
) -> None:
    """The async endpoint walks every entry exactly once, in order."""
    pages = await _awalk_pagination(
        dmr_async_client,
        reverse(view_name),
        {'order_by': order_by, 'limit': limit},
    )
    _assert_walk(pages, seeded_entries, order_by, limit)
