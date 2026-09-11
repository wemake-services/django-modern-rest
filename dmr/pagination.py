import dataclasses
from collections.abc import Sequence
from typing import Generic, TypeVar

_ModelT = TypeVar('_ModelT')


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Page(Generic[_ModelT]):
    """
    Default page model for serialization.

    Can be used when using pagination with ``django-modern-rest``.

    Attributes:
        number: Page number. For example: ``5`` page out of ``10`` total pages.
        object_list: Generic sequence of objects on this page.

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

    Attributes:
        count: Total count of all objects that we are paginating.
        num_pages: Total number of pages that we got after pagination.
        per_page: Number of objects per one page.
        page: :class:`Page` object that contains paginated objects on this page.

    """

    count: int
    num_pages: int
    per_page: int
    page: Page[_ModelT]
