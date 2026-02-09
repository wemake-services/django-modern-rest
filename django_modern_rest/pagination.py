import dataclasses
from collections.abc import Sequence
from typing import Generic, TypeVar

_ModelT = TypeVar('_ModelT')


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Page(Generic[_ModelT]):
    """
    Default page model.

    Can be used when using pagination with ``django_modern_rest``.
    """

    number: int
    object_list: Sequence[_ModelT]


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class Paginated(Generic[_ModelT]):
    """
    Helper type to help serializer the default ``Paginator`` object.

    Django already ships a pagination system, we don't want to replicate it.
    So, we only provide metadata.
    See :class:`django.core.paginator.Paginator` for the exact API.
    """

    count: int
    num_pages: int
    page: Page[_ModelT]
