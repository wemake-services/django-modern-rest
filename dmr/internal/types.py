
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from dmr.errors import ErrorType


class FormatError(Protocol):
    """Callable that formats an error into :class:`~dmr.errors.ErrorModel`."""

    def __call__(
        self,
        error: str | Exception,
        *,
        loc: str | None = None,
        error_type: 'str | ErrorType | None' = None,
    ) -> Any:
        """Format an error into simple python object."""
        ...
