from typing import Generic

from typing_extensions import TypeVar, override

from dmr.security.jwt import views
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)

#: Cookie views send their tokens in cookies, the body is empty by default.
_CookieResponseT = TypeVar('_CookieResponseT', default=None)


class CookieObtainTokensSyncController(
    views.CookieObtainTokensSyncController[
        _SerializerT,
        views.ObtainTokensPayload,
        _CookieResponseT,
    ],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Sync controller to issue both tokens as cookies, almost ready to be routed.

    Takes :class:`~dmr.security.jwt.views.ObtainTokensPayload`
    and answers with an empty ``204 No Content`` and both cookies set.

    ``jwt_refresh_cookie_path`` is still required,
    it has no default on purpose: it scopes the refresh cookie
    to your refresh endpoint, so the refresh token is not sent
    with any other request.

    .. code:: python

        class Login(CookieObtainTokensSyncController[PydanticSerializer]):
            jwt_refresh_cookie_path = reverse_lazy('api:refresh')

    See :class:`~dmr.security.jwt.views.CookieObtainTokensSyncController`
    for all the cookie settings and hooks it inherits,
    switch to it when the default request body does not fit.

    .. versionadded:: 0.16.0
    """

    @override
    def convert_auth_payload(
        self,
        payload: views.ObtainTokensPayload,
    ) -> views.ObtainTokensPayload:
        """Default payload is already what ``authenticate`` expects."""
        return payload


class CookieObtainTokensAsyncController(
    views.CookieObtainTokensAsyncController[
        _SerializerT,
        views.ObtainTokensPayload,
        _CookieResponseT,
    ],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Async controller to issue both tokens as cookies.

    Async version of
    :class:`~dmr.security.jwt.concrete_views.CookieObtainTokensSyncController`.

    .. versionadded:: 0.16.0
    """

    @override
    async def convert_auth_payload(
        self,
        payload: views.ObtainTokensPayload,
    ) -> views.ObtainTokensPayload:
        """Default payload is already what ``aauthenticate`` expects."""
        return payload
