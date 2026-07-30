from typing import TYPE_CHECKING, Literal, overload

from django.http import HttpRequest

if TYPE_CHECKING:
    from dmr.security.token.token import TokenLikeAsync, TokenLikeSync


@overload
def request_token(
    request: HttpRequest,
    *,
    strict: Literal[True],
    sync: Literal[False],
) -> 'TokenLikeAsync': ...


@overload
def request_token(
    request: HttpRequest,
    *,
    strict: Literal[True],
    sync: Literal[True] = True,
) -> 'TokenLikeSync': ...


@overload
def request_token(
    request: HttpRequest,
    *,
    strict: bool = False,
    sync: Literal[False],
) -> 'TokenLikeAsync | None': ...


@overload
def request_token(
    request: HttpRequest,
    *,
    strict: bool = False,
    sync: Literal[True] = True,
) -> 'TokenLikeSync | None': ...


def request_token(
    request: HttpRequest,
    *,
    strict: bool = False,
    sync: bool = True,
) -> 'TokenLikeSync | TokenLikeAsync | None':
    """
    Return the TokenLike from request, if it was authed with one.

    Raises:
        AttributeError: When *strict* is passed and *request* has no token.
        TypeError: When *sync* boolean does not match the token interface.

    """
    from dmr.security.token.token import (  # noqa: PLC0415
        TokenLikeAsync,
        TokenLikeSync,
    )

    token = getattr(request, '__dmr_token__', None)
    if token is None:
        if strict:
            raise AttributeError('__dmr_token__')
        return None

    wrong_sync = (
        not isinstance(token, TokenLikeSync)
        if sync
        else not isinstance(token, TokenLikeAsync)
    )
    if wrong_sync:
        raise TypeError(
            'Token interface does not match the requested sync mode',
        )
    return token  # type: ignore[no-any-return]
