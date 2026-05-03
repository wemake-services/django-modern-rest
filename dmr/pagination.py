import dataclasses
from base64 import b64decode, b64encode
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from django.db.models import Model, Q, QuerySet, TextField, Value

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

    total: int
    next_cursor: str | None = None
    prev_cursor: str | None = None
    page: Page[_ModelT]


@dataclasses.dataclass(frozen=True, kw_only=True)
class InvalidCursorError(Exception):
    """Invalid cursor."""

    message: str = 'Invalid cursor'


NONE_STRING = '::None'


class CursorPaginator(Generic[_DjangoModelT]):
    """Cursor Paginator."""

    def __init__(
        self,
        ordering_fields: tuple[str, ...],
        query_set: QuerySet[_DjangoModelT],
    ) -> None:
        self.ordering_fields = ordering_fields
        self.query_set = query_set

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

    def _encode_cursor(
        self,
        cursor_values: tuple[str, ...],
        delimiter: str = ',',
    ) -> str:
        return b64encode(
            delimiter.join(cursor_values).encode('utf-8'),
        ).decode(
            'ascii',
        )

    def _filter(
        self,
        ordering_fields: tuple[str, ...],
        cursor_values: tuple[str | None, ...],
        from_last: bool = False,
        reverse: bool = False,
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
                if from_last:
                    q = {key: False}
                    q.update(q_equality)
                    filtering |= Q(**q)

                q_equality.update({key: True})
                continue
            comparison_key = (
                f'{ord_field}__lt'
                if reverse != is_reversed
                else f'{ord_field}__gt'
            )
            q = Q(**{comparison_key: value})
            if not from_last:
                q |= Q(**{f'{ord_field}__isnull': True})
            filtering |= (q) & Q(**q_equality)

            equality_key = f'{ord_field}__exact'
            q_equality.update({equality_key: value})
        return filtering

    def _apply_cursor(
        self,
        cursor: str,
        query_set: QuerySet[_DjangoModelT],
        from_last: bool,
        reverse: bool = False,
    ) -> QuerySet[_DjangoModelT]:
        cursor_values = self._decode_cursor(cursor)
        return query_set.filter(
            self._filter(
                ordering_fields=self.ordering_fields,
                cursor_values=cursor_values,
                from_last=from_last,
                reverse=reverse,
            ),
        )

    def page(
        self,
        per_page: int,
        cursor: str | None = None,
    ) -> CursorPaginated[_DjangoModelT]:
        raise NotImplementedError
