from typing import TYPE_CHECKING, Literal, overload

from django.http import HttpRequest

if TYPE_CHECKING:
    from dmr.security.token.models import Token


@overload
def request_token(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> 'Token': ...


@overload
def request_token(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'Token | None': ...


def request_token(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'Token | None':
    """
    Return the Token from request, if it was authed with one.

    When *strict* is passed and *request* has no token,
    we raise :exc:`AttributeError`.
    """
    token = getattr(request, '__dmr_token__', None)
    if token is None and strict:
        raise AttributeError('__dmr_token__')
    return token
