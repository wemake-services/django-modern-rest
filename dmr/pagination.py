import dataclasses
from base64 import b64decode, b64encode
from collections.abc import Sequence
from typing import Any, Generic, Protocol, TypeVar, override

from django.db import models

_ModelT = TypeVar('_ModelT')
_DjangoModelT = TypeVar('_DjangoModelT', bound=models.Model)


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
    object_list: Sequence[_ModelT]


@dataclasses.dataclass(frozen=True, kw_only=True)
class InvalidCursorError(Exception):
    """Invalid cursor."""

    message: str = 'Invalid cursor'


NONE_STRING = '::None'
REWERSE_ORDER_PREFIX = '-'


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


class DjangoCursorPaginator(  # noqa: WPS214
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
        query_set: models.QuerySet[_DjangoModelT],
    ) -> None:
        """
        Create a paginator.

        Args:
            ordering_fields: Fields to order by. To reverse the order, use the
            `-` symbol sign before the field names (for example, `-created_at`).
            query_set: QuerySet which will used to paginate.
        """
        self.ordering_fields = ordering_fields
        self.query_set = query_set

    @override
    async def page(
        self,
        per_page: int,
        cursor: str | None = None,
    ) -> CursorPaginated[_DjangoModelT]:
        """
        Get page with provided cursor.

        If `cursor == None`, the first page will be returned by default.
        """
        if not await self.query_set.aexists():
            return CursorPaginated(
                next_cursor=None,
                prev_cursor=None,
                object_list=[],
            )

        query_set = self.query_set.order_by(
            *self._get_ordering(self.ordering_fields),
        )

        if cursor is not None:
            query_set = self._apply_cursor(cursor, query_set)[: per_page + 1]

        return await self._paginated(query_set, per_page)

    @override
    async def prev_page(
        self,
        per_page: int,
        cursor: str,
    ) -> CursorPaginated[_DjangoModelT]:
        """Get the page that was before the page of the provided cursor."""
        if not await self.query_set.aexists():
            return CursorPaginated(
                next_cursor=None,
                prev_cursor=None,
                object_list=[],
            )

        query_set = self.query_set.order_by(
            *self._get_reverse_ordering(
                self._reverse_fields_ordering(self.ordering_fields),
            ),
        )
        query_set = self._apply_reverse_cursor(
            cursor,
            query_set,
        )[: per_page + 1]

        return await self._paginated(query_set, per_page, prev_page=True)

    async def _paginated(
        self,
        query_set: models.QuerySet[_DjangoModelT],
        per_page: int,
        prev_page: bool = False,  # noqa: FBT001, FBT002
    ) -> CursorPaginated[_DjangoModelT]:
        page_objects = [obj async for obj in query_set[: per_page + 1]]  # noqa: WPS110

        has_next = len(page_objects) > per_page
        page_objects = page_objects[:per_page]
        if prev_page:
            page_objects.reverse()

        next_cursor = self._cursor(page_objects[-1]) if has_next else None
        prev_cursor = self._cursor(page_objects[0]) if page_objects else None

        return CursorPaginated(
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            object_list=page_objects,
        )

    def _get_ordering(
        self,
        ordering_fields: tuple[str, ...],
    ) -> list[models.OrderBy]:
        nulls_ordering: list[models.OrderBy] = []
        for field in ordering_fields:
            column = field.lstrip(REWERSE_ORDER_PREFIX)

            if field.startswith(REWERSE_ORDER_PREFIX):
                nulls_ordering.append(models.F(column).desc(nulls_last=True))
                continue
            nulls_ordering.append(models.F(column).asc(nulls_last=True))
        return nulls_ordering

    def _get_reverse_ordering(
        self,
        ordering_fields: tuple[str, ...],
    ) -> list[models.OrderBy]:
        nulls_ordering: list[models.OrderBy] = []
        for field in ordering_fields:
            column = field.lstrip(REWERSE_ORDER_PREFIX)

            if field.lstrip(REWERSE_ORDER_PREFIX):
                nulls_ordering.append(models.F(column).asc(nulls_first=True))
                continue
            nulls_ordering.append(models.F(column).desc(nulls_first=True))
        return nulls_ordering

    def _common_filter(  # noqa: WPS210
        self,
        ordering_fields: tuple[str, ...],
        cursor_values: tuple[str | None, ...],
    ) -> models.Q:
        if not ordering_fields or not cursor_values:
            return models.Q()
        if len(ordering_fields) != len(cursor_values):
            raise ValueError('Ordering and cursor values must match length')

        position_values = [
            None
            if pos is None
            else models.Value(pos, output_field=models.TextField())
            for pos in cursor_values
        ]

        filtering = models.Q()
        filtering_equality: dict[str, Any] = {}

        # We just checked above that length of ordering_fields == cursor_values
        for ordering_field, position_value in zip(  # noqa: B905
            ordering_fields,
            position_values,
        ):
            is_reversed = ordering_field.startswith(REWERSE_ORDER_PREFIX)
            order = ordering_field.lstrip(REWERSE_ORDER_PREFIX)

            if position_value is None:
                filtering_equality.update({f'{order}__isnull': True})
                continue

            comparison_key = f'{order}__lt' if is_reversed else f'{order}__gt'
            node = models.Q(**{comparison_key: position_value})
            node |= models.Q(**{f'{order}__isnull': True})
            filtering |= (node) & models.Q(**filtering_equality)

            filtering_equality.update({f'{order}__exact': position_value})
        return filtering

    def _reverse_filter(  # noqa: WPS210
        self,
        ordering_fields: tuple[str, ...],
        cursor_values: tuple[str | None, ...],
    ) -> models.Q:
        if not ordering_fields or not cursor_values:
            return models.Q()
        if len(ordering_fields) != len(cursor_values):
            raise ValueError('Ordering and cursor values must match length')

        position_values = [
            None
            if pos_value is None
            else models.Value(pos_value, output_field=models.TextField())
            for pos_value in cursor_values
        ]

        filtering = models.Q()
        q_equality: dict[str, Any] = {}

        # We just checked above that length of ordering_fields == cursor_values
        for ordering_field, pos_value in zip(  # noqa: B905
            ordering_fields,
            position_values,
        ):
            is_reversed = ordering_field.startswith(REWERSE_ORDER_PREFIX)
            order = ordering_field.lstrip(REWERSE_ORDER_PREFIX)

            if pos_value is None:
                node = {f'{order}__isnull': False}
                node.update(q_equality)
                filtering |= models.Q(**node)

                q_equality.update({f'{order}__isnull': True})
                continue
            comparison_key = f'{order}__gt' if is_reversed else f'{order}__lt'
            # Mypy warns that variable `node` has different type than
            # the type from the `if` statement above, but it is normal
            # because we don't reuse this variable, we only assign a new
            # value at each iteration.
            node = {comparison_key: pos_value}  # type: ignore[dict-item]
            filtering |= models.Q(**node) & models.Q(**q_equality)

            q_equality.update({f'{order}__exact': pos_value})
        return filtering

    def _apply_cursor(
        self,
        cursor: str,
        query_set: models.QuerySet[_DjangoModelT],
    ) -> models.QuerySet[_DjangoModelT]:
        return query_set.filter(
            self._common_filter(
                ordering_fields=self.ordering_fields,
                cursor_values=self._decode_cursor(cursor),
            ),
        )

    def _apply_reverse_cursor(
        self,
        cursor: str,
        query_set: models.QuerySet[_DjangoModelT],
    ) -> models.QuerySet[_DjangoModelT]:
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
            field_path = order.lstrip(REWERSE_ORDER_PREFIX).split('__')

            attr = instance
            for field in field_path:
                attr = getattr(attr, field, None)
            position.append(NONE_STRING if attr is None else str(attr))
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
            return tuple(
                None if cursor_value == NONE_STRING else cursor_value
                for cursor_value in b64decode(cursor.encode('ascii'))
                .decode('utf-8')
                .split(delimiter)
            )
        except (TypeError, ValueError):
            raise InvalidCursorError from None

    def _reverse_fields_ordering(
        self,
        ordering_fields: tuple[str, ...],
    ) -> tuple[str, ...]:
        # Convert '-created_at' to 'created_at' and vice versa
        return tuple(
            field[1:]
            if field.startswith(REWERSE_ORDER_PREFIX)
            else f'{REWERSE_ORDER_PREFIX}{field}'
            for field in ordering_fields
        )
