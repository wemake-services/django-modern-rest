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
