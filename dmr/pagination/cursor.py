import base64
import dataclasses
from collections.abc import Callable, Sequence
from http import HTTPStatus
from typing import Any, ClassVar, Generic, TypeVar, final

from django.db import models
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from dmr.internal.django import get_model_pks

_ModelT = TypeVar('_ModelT')
_DjangoModel = TypeVar('_DjangoModel', bound=models.Model)


@final
class InvalidCursorError(Exception):
    """
    Raised when a pagination cursor cannot be decoded or validated.

    The cursor is a client-provided value,
    so a malformed one is a client error.
    """

    default_message: ClassVar[str | Promise] = _('Invalid cursor')
    status_code: ClassVar[HTTPStatus] = HTTPStatus.BAD_REQUEST

    def __init__(
        self,
        msg: str | Promise | None = None,
    ) -> None:
        """Provides default error message."""
        super().__init__(msg or self.default_message)


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class CursorPaginated(Generic[_ModelT]):
    """
    Helper for returning cursor paginated response.

    Attributes:
        next_cursor: Encoded cursor to request the next page.
            ``None`` when there are no more pages.
        per_page: Number of objects per one page.
        page: Generic sequence of objects on this page.

    """

    next_cursor: str | None
    per_page: int
    page: Sequence[_ModelT]


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class CursorPage(Generic[_DjangoModel]):
    """
    Helper type for cursor pagination responses.

    ``next_cursor`` is ``None`` when there are no more objects,
    ``objects_list`` holds the objects of the current page.

    Attributes:
        next_cursor: Encoded cursor to request the next page.
            ``None`` when there are no more items after this page.
        objects_list: Sequence of objects on this page.

    """

    next_cursor: str | None
    objects_list: Sequence[_DjangoModel]


def _default_cursor_encoder(cursor: str) -> str:
    """Default function used to encode a cursor."""
    return base64.urlsafe_b64encode(cursor.encode()).decode('utf-8')


def _default_cursor_decoder(cursor: str) -> str:
    """Default function used to decode a cursor."""
    return base64.urlsafe_b64decode(cursor).decode('utf-8')


class _BaseCursorPaginator(Generic[_DjangoModel]):
    """
    Base cursor paginator.

    Class has useful utilities used by
    both sync and async versions.

    The cursor ordering is taken from the queryset ``order_by``:
    primary key fields are appended automatically
    as tiebreakers to keep it stable.

    Attributes:
        per_page: Number of objects per one page.

    """

    __slots__ = (
        '_cursor_decoder',
        '_cursor_encoder',
        '_order_by_field_names',
        '_order_by_fields',
        '_queryset',
        '_separator',
        'per_page',
    )

    def __init__(
        self,
        queryset: 'models.QuerySet[_DjangoModel]',
        per_page: int,
        cursor_encoder: Callable[[str], str] | None = None,
        cursor_decoder: Callable[[str], str] | None = None,
        separator: str = '|-|',
    ) -> None:
        """
        Create a paginator over ``queryset``.

        The queryset must be ordered: its ``order_by`` defines
        the cursor ordering, and the primary key fields are
        appended automatically as tiebreakers to keep it stable.
        """
        if per_page <= 0:
            raise ValueError('`per_page` should be a positive integer!')

        self._queryset = queryset
        self.per_page = per_page
        self._cursor_encoder = cursor_encoder or _default_cursor_encoder
        self._cursor_decoder = cursor_decoder or _default_cursor_decoder
        self._separator = separator
        self._order_by_fields: list[str] = []
        self._order_by_field_names: list[str] = []
        self._make_ordering()

    def encode_cursor(self, cursor_attrs: dict[str, Any]) -> str:
        """Build an encoded cursor from the ``cursor_attrs`` values."""
        return self._cursor_encoder(
            self._separator.join([
                str(cursor_attrs[attr_name])
                for attr_name in self._order_by_field_names
            ]),
        )

    def apply_cursor_filter(
        self,
        cursor: str,
    ) -> None:
        """
        Filter the queryset to rows that follow the given *cursor*.

        Implements a lexicographic comparison over the ``order_by`` fields,
        so the ordering must end with a unique field (usually the primary key)
        to avoid skipping or duplicating rows.
        """
        decoded_cursor = self._decode_cursor(cursor)
        cursor_q = models.Q()
        equalities: dict[str, str] = {}
        for index, order_by_field in enumerate(self._order_by_fields):
            cursor_q |= self._add_cursor_condition(
                order_by_field,
                equalities,
                index,
                decoded_cursor,
            )
            # After we added cursor condition, we update
            # equalities with the field we just processed,
            # so it will be used in the upcoming iterations.
            equalities[self._order_by_field_names[index]] = decoded_cursor[
                index
            ]
        self._queryset = self._queryset.filter(cursor_q)

    def _add_cursor_condition(
        self,
        order_by_field: str,
        equalities: dict[str, str],
        index: int,
        decoded_cursor: list[str],
    ) -> models.Q:
        """
        Create a filtering condition for the cursor.

        Cursor keyset pagination consists of many filters,
        not just one.

        So, for each ordering field, we also need
        to check the case when it is equal.

        For instance, if you have a table with a field ``name``,
        which is not unique, we need to add all of the primary keys
        to ensure consistency of cursor pagination.

        So, for this particular case, we need to build the following SQL:

        .. code-block:: sql

            (name > cursor.name)
            OR (name = cursor.name AND pk1 > cursor.pk1)
            OR (name = cursor.name AND pk1 = cursor.pk1 AND pk2 > cursor.pk2)

        Arguments:
            order_by_field: Field name to add condition for.
            equalities: Dictionary of equality conditions for previous fields.
            index: Index of the current field in the order_by list.
            decoded_cursor: List of decoded cursor values.

        """
        lookup = 'lt' if order_by_field.startswith('-') else 'gt'
        return models.Q(
            **equalities,
            **{
                f'{self._order_by_field_names[index]}__{lookup}': (
                    decoded_cursor[index]
                ),
            },
        )

    def _decode_cursor(self, cursor: str) -> list[str]:
        """Decode a cursor into its ordered field values."""
        try:
            decoded_cursor = self._cursor_decoder(cursor).split(self._separator)
        except Exception as exc:
            # Covers both the default decoder cases:
            # invalid base64 and non-utf-8 payload:
            raise InvalidCursorError(
                'The cursor cannot be decoded!',
            ) from exc

        if len(decoded_cursor) != len(self._order_by_field_names):
            raise InvalidCursorError(
                f'Cursor has {len(decoded_cursor)} fields, '
                f'but {len(self._order_by_field_names)} were expected!',
            )
        return decoded_cursor

    def _make_ordering(self) -> None:
        """
        Prepare queryset for ordering and cache fields.

        This function calculates order_by that will
        be consistent across different cursor requests.

        It preserves original order_by ordering and
        adds primary key fields if they were not present
        in original order_by.
        """
        orderby_fields: list[str] = []
        field_names: set[str] = set()
        for orderby in self._queryset.query.order_by:
            if not isinstance(orderby, str):
                raise TypeError('Only str arguments are supported in orderby')
            orderby_fields.append(orderby)
            field_names.add(orderby.removeprefix('-'))
        pks = [
            pk.name
            for pk in get_model_pks(self._queryset.model)
            if pk.name not in field_names
        ]

        self._order_by_fields = [*orderby_fields, *pks]
        self._order_by_field_names = [
            field.removeprefix('-') for field in self._order_by_fields
        ]
        self._queryset = self._queryset.order_by(*self._order_by_fields)


class CursorPaginator(
    _BaseCursorPaginator[_DjangoModel],
    Generic[_DjangoModel],
):
    """Cursor paginator."""

    __slots__ = ()

    def page(self, cursor: str | None = None) -> CursorPage[_DjangoModel]:
        """
        Return the page that starts after ``cursor``.

        When ``cursor`` is ``None``, the first page is returned.
        """
        if cursor:
            self.apply_cursor_filter(cursor)

        objects_list = list(self._queryset[: self.per_page])

        next_cursor = None
        if len(objects_list) == self.per_page:
            cursor_attrs = (
                self._queryset
                .filter(pk=objects_list[-1].pk)
                .values(*self._order_by_field_names)
                .get()
            )
            next_cursor = self.encode_cursor(cursor_attrs)

        return CursorPage(
            next_cursor=next_cursor,
            objects_list=objects_list,
        )

    async def apage(
        self,
        cursor: str | None = None,
    ) -> CursorPage[_DjangoModel]:
        """
        Async version of :meth:`CursorPaginator.page`.

        Returns the page that starts after ``cursor``.

        When ``cursor`` is ``None``, the first page is returned.
        """
        if cursor:
            self.apply_cursor_filter(cursor)

        objects_list = [
            object_item
            async for object_item in self._queryset[: self.per_page].aiterator(
                chunk_size=self.per_page,
            )
        ]

        next_cursor = None
        if len(objects_list) == self.per_page:
            cursor_attrs = await (
                self._queryset
                .filter(pk=objects_list[-1].pk)
                .values(*self._order_by_field_names)
                .aget()
            )
            next_cursor = self.encode_cursor(cursor_attrs)

        return CursorPage(
            next_cursor=next_cursor,
            objects_list=objects_list,
        )
