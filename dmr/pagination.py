import dataclasses
from base64 import b64decode, b64encode
from collections.abc import Sequence
from typing import Any, Generic, Protocol, TypeVar

from django.db.models import F, Model, OrderBy, Q, QuerySet, TextField, Value

_ModelT = TypeVar('_ModelT')
_DjangoModelT = TypeVar('_DjangoModelT', bound=Model)


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Page(Generic[_ModelT]):
    """
    Default page model for serialization.

    Can be used when using pagination with ``django-modern-rest``.
    """

    number: int
    # Does not support `_SupportsPagination` type,
    # explicit type cast to `list` or `tuple` is required,
    # because it is hard to serialize complex `_SupportsPagination` protocol.
    object_list: Sequence[_ModelT]


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Paginated(Generic[_ModelT]):
    """
    Helper type to serialize the default ``Paginator`` object.

    Django already ships a pagination system, we don't want to replicate it.
    So, we only provide metadata.
    See :class:`django.core.paginator.Paginator` for the exact API.
    """

    count: int
    num_pages: int
    per_page: int
    page: Page[_ModelT]


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class CursorPaginated(Generic[_ModelT]):
    """Cursor Paginated."""

    next_cursor: str | None = None
    prev_cursor: str | None = None
    items: Sequence[_ModelT]


@dataclasses.dataclass(frozen=True, kw_only=True)
class InvalidCursorError(Exception):
    """Invalid cursor."""

    message: str = 'Invalid cursor'


NONE_STRING = '::None'


class SyncCursorPaginator(Protocol, Generic[_ModelT]):
    """Protocol for synchronous cursor pagination."""

    def page(
        self,
        per_page: int,
        cursor: str | None = None,
    ) -> CursorPaginated[_ModelT]:
        """Get page with provided cursor."""
        raise NotImplementedError

    def prev_page(
        self,
        per_page: int,
        cursor: str,
    ) -> CursorPaginated[_ModelT]:
        """Get the page that was before the page of the provided cursor."""
        raise NotImplementedError


class AsyncCursorPaginator(Protocol, Generic[_ModelT]):
    """Protocol for asynchronous cursor pagination."""

    async def page(
        self,
        per_page: int,
        cursor: str | None = None,
    ) -> CursorPaginated[_ModelT]:
        """Get page with provided cursor."""
        raise NotImplementedError

    async def prev_page(
        self,
        per_page: int,
        cursor: str,
    ) -> CursorPaginated[_ModelT]:
        """Get the page that was before the page of the provided cursor."""
        raise NotImplementedError


class DjangoCursorPaginator(
    AsyncCursorPaginator[_DjangoModelT],
    Generic[_DjangoModelT],
):
    """
    The default implementation of the asynchronous cursor for django.

    It was based on the implementation from `django-cursor-pagination`, but with
    our own API and a bit refactoring.
    """

    def __init__(
        self,
        ordering_fields: tuple[str, ...],
        query_set: QuerySet[_DjangoModelT],
    ) -> None:
        """
        Create a paginator.

        Args:
            ordering_fields: Fields to order by.
            query_set: QuerySet which will used to paginate.
        """
        self.ordering_fields = ordering_fields
        self.query_set = query_set

    async def page(
        self,
        per_page: int,
        cursor: str | None = None,
    ) -> CursorPaginated[_DjangoModelT]:
        """
        Get page with provided cursor.

        If `cursor == None`, the first page will be received by default.
        """
        if not self.query_set.exists():
            return CursorPaginated(
                next_cursor=None,
                prev_cursor=None,
                items=[],
            )

        query_set = self.query_set.order_by(
            *self._get_ordering(self.ordering_fields),
        )

        if cursor is not None:
            query_set = self._apply_cursor(cursor, query_set)[: per_page + 1]

        return await self._paginated(query_set, per_page)

    async def prev_page(
        self,
        per_page: int,
        cursor: str,
    ) -> CursorPaginated[_DjangoModelT]:
        """Get the page that was before the page of the provided cursor."""
        if not self.query_set.exists():
            return CursorPaginated(
                next_cursor=None,
                prev_cursor=None,
                items=[],
            )

        query_set = self.query_set.order_by(
            *self._get_reverse_ordering(
                self._reverse_ordering(self.ordering_fields),
            ),
        )
        query_set = self._apply_reverse_cursor(
            cursor,
            query_set,
        )[: per_page + 1]

        return await self._paginated(query_set, per_page)

    def _get_ordering(
        self,
        ordering_fields: tuple[str, ...],
    ) -> list[OrderBy]:
        nulls_ordering: list[OrderBy] = []
        for field in ordering_fields:
            reverse = field.startswith('-')
            column = field.lstrip('-')

            if reverse:
                nulls_ordering.append(F(column).desc(nulls_last=True))
                continue
            nulls_ordering.append(F(column).asc(nulls_last=True))
        return nulls_ordering

    def _get_reverse_ordering(
        self,
        ordering_fields: tuple[str, ...],
    ) -> list[OrderBy]:
        nulls_ordering: list[OrderBy] = []
        for field in ordering_fields:
            reverse = field.startswith('-')
            column = field.lstrip('-')

            if reverse:
                nulls_ordering.append(F(column).asc(nulls_first=True))
                continue
            nulls_ordering.append(F(column).desc(nulls_first=True))
        return nulls_ordering

    def _filter(
        self,
        ordering_fields: tuple[str, ...],
        cursor_values: tuple[str | None, ...],
    ) -> Q:
        if not ordering_fields or not cursor_values:
            return Q()
        if len(ordering_fields) != len(cursor_values):
            raise ValueError('Ordering and cursor values must match length')

        position_values = [
            Value(pos, output_field=TextField()) if pos is not None else None
            for pos in cursor_values
        ]

        filtering = Q()
        q_equality: dict[str, Any] = {}

        # We just checked above that length of ordering_fields == cursor_values
        for ordering_field, value in zip(ordering_fields, position_values):  # noqa: B905
            is_reversed = ordering_field.startswith('-')
            ord_field = ordering_field.lstrip('-')

            if value is None:
                key = f'{ord_field}__isnull'

                q_equality.update({key: True})
                continue
            comparison_key = (
                f'{ord_field}__gt' if is_reversed else f'{ord_field}__lt'
            )
            q = Q(**{comparison_key: value})
            q |= Q(**{f'{ord_field}__isnull': True})
            filtering |= (q) & Q(**q_equality)

            equality_key = f'{ord_field}__exact'
            q_equality.update({equality_key: value})
        return filtering

    def _reverse_filter(
        self,
        ordering_fields: tuple[str, ...],
        cursor_values: tuple[str | None, ...],
    ) -> Q:
        if not ordering_fields or not cursor_values:
            return Q()
        if len(ordering_fields) != len(cursor_values):
            raise ValueError('Ordering and cursor values must match length')

        position_values = [
            Value(pos, output_field=TextField()) if pos is not None else None
            for pos in cursor_values
        ]

        filtering = Q()
        q_equality: dict[str, Any] = {}

        # We just checked above that length of ordering_fields == cursor_values
        for ordering_field, value in zip(ordering_fields, position_values):  # noqa: B905
            is_reversed = ordering_field.startswith('-')
            ord_field = ordering_field.lstrip('-')

            if value is None:
                key = f'{ord_field}__isnull'
                q = {key: False}
                q.update(q_equality)
                filtering |= Q(**q)

                q_equality.update({key: True})
                continue
            comparison_key = (
                f'{ord_field}__lt' if is_reversed else f'{ord_field}__gt'
            )
            q = Q(**{comparison_key: value})
            filtering |= (q) & Q(**q_equality)

            equality_key = f'{ord_field}__exact'
            q_equality.update({equality_key: value})
        return filtering

    def _apply_cursor(
        self,
        cursor: str,
        query_set: QuerySet[_DjangoModelT],
    ) -> QuerySet[_DjangoModelT]:
        return query_set.filter(
            self._filter(
                ordering_fields=self.ordering_fields,
                cursor_values=self._decode_cursor(cursor),
            ),
        )

    def _apply_reverse_cursor(
        self,
        cursor: str,
        query_set: QuerySet[_DjangoModelT],
    ) -> QuerySet[_DjangoModelT]:
        return query_set.filter(
            self._reverse_filter(
                ordering_fields=self.ordering_fields,
                cursor_values=self._decode_cursor(cursor),
            ),
        )

    def _cursor(self, instance: _DjangoModelT | None) -> str:
        return self._encode_cursor(self._position_from_instance(instance))

    def _position_from_instance(
        self,
        instance: _DjangoModelT | None,
    ) -> list[str]:
        position: list[str] = []
        for order in self.ordering_fields:
            parts = order.lstrip('-').split('__')
            attr = instance
            while parts:
                attr = getattr(attr, parts[0])
                parts.pop(0)
            if attr is None:
                position.append(NONE_STRING)
            else:
                position.append(str(attr))
        return position

    def _encode_cursor(
        self,
        cursor_values: list[str],
        delimiter: str = ',',
    ) -> str:
        return b64encode(
            delimiter.join(cursor_values).encode('utf-8'),
        ).decode(
            'ascii',
        )

    def _decode_cursor(
        self,
        cursor: str,
        delimiter: str = ',',
    ) -> tuple[str | None, ...]:
        try:
            cursor_values = b64decode(cursor.encode('ascii')).decode('utf-8')
            return tuple(
                value if value != NONE_STRING else None
                for value in cursor_values.split(delimiter)
            )
        except (TypeError, ValueError):
            raise InvalidCursorError from None

    async def _paginated(
        self,
        query_set: QuerySet[_DjangoModelT],
        per_page: int,
    ) -> CursorPaginated[_DjangoModelT]:
        items = [item async for item in query_set.aiterator()]
        has_next = len(items) > per_page

        items = items[:per_page]
        items.reverse()
        next_cursor = self._cursor(items[-1]) if has_next else None
        prev_cursor = self._cursor(items[0]) if items else None
        return CursorPaginated(
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            items=items,
        )

    def _reverse_ordering(
        self,
        ordering_fields: tuple[str, ...],
    ) -> tuple[str, ...]:
        def invert(x: str) -> str:
            return x[1:] if (x.startswith('-')) else '-' + x

        return tuple(invert(field) for field in ordering_fields)
