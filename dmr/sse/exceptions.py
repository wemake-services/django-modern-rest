from typing import final


@final
class SSECloseConnectionError(Exception):
    """
    Raised when we need to imediatelly close the response stream.

    Raise it from events producing async iterator.
    """
