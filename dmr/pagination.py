import dataclasses
from base64 import b64decode, b64encode
from collections.abc import Sequence
from typing import Generic, TypeVar

from django.db.models import Model, QuerySet

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


class CursorPaginator(Generic[_DjangoModelT]):
    """Cursor Paginator."""

    def __init__(self, query_set: QuerySet[_DjangoModelT]) -> None:
        self.query_set = query_set

    def _decode_cursor(self, cursor: str, delimiter: str = ',') -> list[str]:
        try:
            ordering_fields = b64decode(cursor.encode('ascii')).decode()
            return list(ordering_fields.split(delimiter))
        except (TypeError, ValueError):
            raise InvalidCursorError from None

    def _encode_cursor(
        self,
        ordering_fields: list[str],
        delimiter: str = ',',
    ) -> str:
        return b64encode(delimiter.join(ordering_fields).encode('utf8')).decode(
            'ascii',
        )

    def page(
        self,
        per_page: int,
        cursor: str,
    ) -> CursorPaginated[_DjangoModelT]:
        raise NotImplementedError
