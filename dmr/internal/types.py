from collections import abc
from collections.abc import AsyncGenerator, AsyncIterator
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Protocol,
    get_args,
    get_origin,
)

if TYPE_CHECKING:
    from dmr.errors import ErrorType


_ASYNC_ITERATOR_TYPES: Final = frozenset((
    abc.AsyncGenerator,
    abc.AsyncIterator,
    AsyncIterator,
    AsyncGenerator,
))


class FormatError(Protocol):
    """Callable that converts an error into a structured Python object."""

    def __call__(
        self,
        error: str | Exception,
        *,
        loc: str | None = None,
        error_type: 'str | ErrorType | None' = None,
    ) -> Any:
        """Return a formatted representation of the given error."""


def call_init_subclass(from_class: type[Any], cls_arg: type[Any]) -> None:
    """Calls ``__init_subclass__`` from a given class with a *cls_arg*."""
    clsmethod = from_class.__dict__['__init_subclass__']
    clsmethod.__func__(cls_arg)


def is_stream_annotation(annotation: Any) -> bool:
    origin = get_origin(annotation)
    type_args = get_args(annotation)
    return bool(type_args) and origin in _ASYNC_ITERATOR_TYPES
