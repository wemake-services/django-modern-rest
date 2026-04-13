from typing import TYPE_CHECKING, Literal, overload

from django.http import HttpRequest

if TYPE_CHECKING:
    from dmr.endpoint import Endpoint


@overload
def request_endpoint(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> 'Endpoint': ...


@overload
def request_endpoint(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'Endpoint | None': ...


def request_endpoint(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'Endpoint | None':
    """
    Return an instance of the ``Endpoint`` that was used for this request.

    When *strict* is passed and *request* has no endpoint,
    we raise :exc:`AttributeError`.
    This can happen for ``405`` responses, for example.
    They don't have endpoints. All others do.
    """
    endpoint = getattr(request, '__dmr_endpoint__', None)
    if endpoint is None and strict:
        raise AttributeError('__dmr_endpoint__')
    return endpoint
