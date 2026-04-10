from typing import final


@final
class StreamingCloseError(Exception):
    """
    Raised when we need to immediately close the response stream.

    Raise it from events producing async iterator.
    """
