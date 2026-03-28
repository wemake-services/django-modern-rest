from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from dmr.errors import ErrorType


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
