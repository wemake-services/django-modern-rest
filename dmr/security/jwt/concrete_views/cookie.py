from typing import TYPE_CHECKING, ClassVar, Generic

from typing_extensions import TypeVar, override

from dmr.security.jwt import views
from dmr.serializer import BaseSerializer

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )

_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)

#: Cookie views send their tokens in cookies, the body is empty by default.
_CookieResponseT = TypeVar('_CookieResponseT', default=None)

#: Widest scope there is, so that a controller works wherever it is routed.
#: Narrow it down to the url of your refresh endpoint, see the class docs.
DEFAULT_REFRESH_COOKIE_PATH: str = '/'


class CookieObtainTokensSyncController(
    views.CookieObtainTokensSyncController[
        _SerializerT,
        views.ObtainTokensPayload,
        _CookieResponseT,
    ],
    Generic[_SerializerT, _CookieResponseT],
):
    """
    Sync controller to issue both tokens as cookies, ready to be routed.

    Takes :class:`~dmr.security.jwt.views.ObtainTokensPayload`
    and answers with an empty ``204 No Content`` and both cookies set:

    .. code:: python

        path('login/', CookieObtainTokensSyncController.as_view(
            serializer=PydanticSerializer,
        ))

    .. warning::

        ``jwt_refresh_cookie_path`` defaults to ``'/'`` here, which sends
        the refresh token with every request to your site. The reusable
        controller has no default on purpose, but a ready-to-use one
        cannot know the url of your refresh endpoint.
        Point it there as soon as you have one, and the refresh token
        stops being sent with anything else:

        .. code:: python

            class Login(CookieObtainTokensSyncController[PydanticSerializer]):
                jwt_refresh_cookie_path = reverse_lazy('api:refresh')

        Every controller that shares the cookies has to agree on the value,
        so change it on the refresh and the logout controller as well.

    See :class:`~dmr.security.jwt.views.CookieObtainTokensSyncController`
    for all the cookie settings and hooks it inherits,
    switch to it when the default request body does not fit.

    .. versionadded:: 0.16.0
    """

    jwt_refresh_cookie_path: ClassVar['_StrOrPromise | None'] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )

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
    Async controller to issue both tokens as cookies, ready to be routed.

    Async version of
    :class:`~dmr.security.jwt.concrete_views.CookieObtainTokensSyncController`,
    including its ``jwt_refresh_cookie_path`` warning.

    .. versionadded:: 0.16.0
    """

    jwt_refresh_cookie_path: ClassVar['_StrOrPromise | None'] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )

    @override
    async def convert_auth_payload(
        self,
        payload: views.ObtainTokensPayload,
    ) -> views.ObtainTokensPayload:
        """Default payload is already what ``aauthenticate`` expects."""
        return payload


class CookieRefreshTokensSyncController(
    views.CookieRefreshTokensSyncController[_SerializerT, _CookieResponseT],
):
    """
    Sync controller to rotate both token cookies, ready to be routed.

    Same as :class:`~dmr.security.jwt.views.CookieRefreshTokensSyncController`,
    only with the same ``jwt_refresh_cookie_path`` default
    as :class:`
    ~dmr.security.jwt.concrete_views.CookieObtainTokensSyncController`,
    so that both ends of the flow agree out of the box.

    .. versionadded:: 0.16.0
    """

    jwt_refresh_cookie_path: ClassVar['_StrOrPromise | None'] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )


class CookieRefreshTokensAsyncController(
    views.CookieRefreshTokensAsyncController[_SerializerT, _CookieResponseT],
):
    """
    Async controller to rotate both token cookies, ready to be routed.

    Async version of
    :class:`~dmr.security.jwt.concrete_views.CookieRefreshTokensSyncController`.

    .. versionadded:: 0.16.0
    """

    jwt_refresh_cookie_path: ClassVar['_StrOrPromise | None'] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )


class CookieLogoutSyncController(
    views.CookieLogoutSyncController[_SerializerT, _CookieResponseT],
):
    """
    Sync controller to drop both token cookies, ready to be routed.

    Same as :class:`~dmr.security.jwt.views.CookieLogoutSyncController`,
    only with the same ``jwt_refresh_cookie_path`` default
    as the rest of this module, so that the cookies it discards
    match the ones that were issued.

    .. versionadded:: 0.16.0
    """

    jwt_refresh_cookie_path: ClassVar['_StrOrPromise | None'] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )


class CookieLogoutAsyncController(
    views.CookieLogoutAsyncController[_SerializerT, _CookieResponseT],
):
    """
    Async controller to drop both token cookies, ready to be routed.

    Async version of
    :class:`~dmr.security.jwt.concrete_views.CookieLogoutSyncController`.

    .. versionadded:: 0.16.0
    """

    jwt_refresh_cookie_path: ClassVar['_StrOrPromise | None'] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )
