import dataclasses
import json
from base64 import b64decode, b64encode
from collections.abc import Sequence
from http import HTTPStatus
from typing import (
    Any,
    ClassVar,
    Generic,
    Protocol,
    TypeVar,
    final,
)

from django.db import models
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _
from typing_extensions import override

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
    """Container for results returned from cursor paginator."""

    object_list: Sequence[_ModelT]
    next_cursor: str | None = None
    prev_cursor: str | None = None


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


@final
class InvalidPaginationCursorError(Exception):
    """Raised when the cursor passed for pagination is invalid."""

    default_message: ClassVar[str | Promise] = _('Invalid cursor')
    status_code: ClassVar[HTTPStatus] = HTTPStatus.BAD_REQUEST

    def __init__(self, msg: str | Promise | None = None) -> None:
        """Provides default error message."""
        # Circular import:
        from dmr.errors import ErrorType  # noqa: PLC0415

        super().__init__(msg or self.default_message)
        self.error_type = ErrorType.value_error


REVERSE_ORDER_PREFIX = '-'


class DjangoCursorPaginator(  # noqa: WPS214
    AsyncCursorPaginator[_DjangoModelT],
    Generic[_DjangoModelT],
):
    """Async cursor paginator to be used with Django ``QuerySet``."""

    def __init__(
        self,
        ordering_fields: tuple[str, ...],
        queryset: models.QuerySet[_DjangoModelT],
    ) -> None:
        """
        Initialize a paginator with ordering fields and a queryset.

        Args:
            ordering_fields: Fields to order by. To reverse the order for the
                field, use the `-` symbol sign before the field name
                (for example, `-created_at`).
            queryset: `QuerySet` to be used for pagination.
        """
        self.ordering_fields = ordering_fields
        self.queryset = queryset

    @override
    async def page(
        self,
        per_page: int,
        cursor: str | None = None,
    ) -> CursorPaginated[_DjangoModelT]:
        """
        Get page with provided cursor.

        Args:
            per_page: Maximum number of objects to be returned in this page.
            cursor: Cursor to get the page. Note that if ``cursor`` is ``None``,
                the first page will be returned by default.

        To continue navigating forward, just use
        :meth:`~dmr.pagination.DjangoCursorPaginator.page`
        again with ``next_cursor``.
        """
        queryset = self.queryset.order_by(
            *self._get_ordering(self.ordering_fields),
        )

        if cursor is None:
            return await self._paginated(queryset, per_page, first_page=True)

        queryset = self._apply_cursor(cursor, queryset)[: per_page + 1]
        return await self._paginated(queryset, per_page, first_page=False)

    @override
    async def prev_page(
        self,
        per_page: int,
        cursor: str,
    ) -> CursorPaginated[_DjangoModelT]:
        """
        Get the page that was before the provided cursor.

        To continue navigating backwards, call
        :meth:`~dmr.pagination.DjangoCursorPaginator.prev_page`
        again with the ``prev_cursor`` returned by the previous
        ``prev_page`` result. To navigate forward again from that
        result, call :meth:`~dmr.pagination.DjangoCursorPaginator.page`
        with its ``next_cursor``.
        """
        queryset = self.queryset.order_by(
            *self._get_reverse_ordering(
                self.ordering_fields,
            ),
        )
        queryset = self._apply_reverse_cursor(
            cursor,
            queryset,
        )[: per_page + 1]

        return await self._reversed_paginated(queryset, per_page)

    async def _paginated(
        self,
        queryset: models.QuerySet[_DjangoModelT],
        per_page: int,
        first_page: bool,  # noqa: FBT001
    ) -> CursorPaginated[_DjangoModelT]:
        page_objects = [obj async for obj in queryset[: per_page + 1]]  # noqa: WPS110

        has_next = len(page_objects) > per_page
        page_objects = page_objects[:per_page]

        next_cursor = self._cursor(page_objects[-1]) if has_next else None
        prev_cursor = (
            self._cursor(page_objects[0])
            if page_objects and not first_page
            else None
        )

        return CursorPaginated(
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            object_list=page_objects,
        )

    async def _reversed_paginated(
        self,
        queryset: models.QuerySet[_DjangoModelT],
        per_page: int,
    ) -> CursorPaginated[_DjangoModelT]:
        page_objects = [obj async for obj in queryset[: per_page + 1]]  # noqa: WPS110

        has_next = len(page_objects) > per_page
        page_objects = page_objects[:per_page]

        next_cursor = self._cursor(page_objects[0]) if page_objects else None
        prev_cursor = self._cursor(page_objects[-1]) if has_next else None

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
            column = field.lstrip(REVERSE_ORDER_PREFIX)

            if field.startswith(REVERSE_ORDER_PREFIX):
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
            column = field.lstrip(REVERSE_ORDER_PREFIX)

            if field.startswith(REVERSE_ORDER_PREFIX):
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
            return models.Q()  # pragma: no cover
        if len(ordering_fields) != len(cursor_values):
            raise ValueError(  # pragma: no cover
                'Ordering and cursor values must match length',
            )

        filtering = models.Q()
        filtering_equality: dict[str, Any] = {}

        # We just checked above that length of ordering_fields == cursor_values
        for ordering_field, position_value in zip(  # noqa: B905
            ordering_fields,
            cursor_values,
        ):
            is_reversed = ordering_field.startswith(REVERSE_ORDER_PREFIX)
            order = ordering_field.lstrip(REVERSE_ORDER_PREFIX)

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
            return models.Q()  # pragma: no cover
        if len(ordering_fields) != len(cursor_values):
            raise ValueError(  # pragma: no cover
                'Ordering and cursor values must match length',
            )

        filtering = models.Q()
        q_equality: dict[str, Any] = {}

        # We just checked above that length of ordering_fields == cursor_values
        for ordering_field, pos_value in zip(  # noqa: B905
            ordering_fields,
            cursor_values,
        ):
            is_reversed = ordering_field.startswith(REVERSE_ORDER_PREFIX)
            order = ordering_field.lstrip(REVERSE_ORDER_PREFIX)

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
        queryset: models.QuerySet[_DjangoModelT],
    ) -> models.QuerySet[_DjangoModelT]:
        return queryset.filter(
            self._common_filter(
                ordering_fields=self.ordering_fields,
                cursor_values=self._decode_cursor(cursor),
            ),
        )

    def _apply_reverse_cursor(
        self,
        cursor: str,
        queryset: models.QuerySet[_DjangoModelT],
    ) -> models.QuerySet[_DjangoModelT]:
        return queryset.filter(
            self._reverse_filter(
                ordering_fields=self.ordering_fields,
                cursor_values=self._decode_cursor(cursor),
            ),
        )

    def _cursor(self, instance: _DjangoModelT) -> str:
        return self._encode_cursor(self._position_from_instance(instance))

    def _position_from_instance(
        self,
        instance: _DjangoModelT,
    ) -> list[str | None]:
        position: list[str | None] = []
        for order in self.ordering_fields:
            field_path = order.lstrip(REVERSE_ORDER_PREFIX).split('__')

            attr: Any = instance
            for field in field_path:
                if attr is None:
                    break
                attr = getattr(attr, field)
            position.append(None if attr is None else str(attr))
        return position

    def _encode_cursor(
        self,
        cursor_values: list[str | None],
    ) -> str:
        return b64encode(
            json.dumps(cursor_values, separators=(',', ':')).encode('utf-8'),
        ).decode('ascii')

    def _decode_cursor(
        self,
        cursor: str,
    ) -> tuple[str | None, ...]:
        try:
            return tuple(
                cursor_val
                for cursor_val in json.loads(
                    b64decode(cursor.encode('ascii')).decode('utf-8'),
                )
            )
        except (UnicodeError, ValueError) as exc:
            raise InvalidPaginationCursorError from exc
