from typing import TypeVar

from django.http import HttpResponseBase

_ResponseT = TypeVar('_ResponseT', bound=HttpResponseBase)


def mark_handled_error(response: _ResponseT) -> _ResponseT:
    """
    Mark a response that we have built for an exception that we handle.

    Users describe the responses that *their* endpoints return.
    Errors that we raise and handle ourselves are not a part of that
    contract, so response validation lets them through
    even when their status code is not described.
    """
    response.__dmr_handled_error__ = True  # type: ignore[attr-defined]
    return response


def is_handled_error(response: HttpResponseBase) -> bool:
    """Tells whether this response was built by our own error handling."""
    return getattr(response, '__dmr_handled_error__', False)
