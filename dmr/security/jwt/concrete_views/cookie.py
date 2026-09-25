from collections.abc import Callable
from typing import Any, ClassVar, Generic, final, Final

from django.http import HttpResponseBase
from typing_extensions import Sentinel, TypeVar, override

from dmr.internal.concrete import build_concrete_controller
from dmr.internal.types import StrOrPromise
from dmr.security.jwt import views
from dmr.serializer import BaseSerializer
from dmr.types import EMPTY

_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)

#: Cookie views send their tokens in cookies, the body is empty by default.
_CookieResponseT = TypeVar('_CookieResponseT', default=None)

#: Widest scope there is, so that a controller works wherever it is routed.
#: Narrow it down to the url of your refresh endpoint, see the class docs.
DEFAULT_REFRESH_COOKIE_PATH: str = '/'


@final
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

        >>> from dmr.plugins.pydantic import PydanticFastSerializer
        >>> from dmr.routing import path
        >>> route = path(
        ...     'login/',
        ...     CookieObtainTokensSyncController.as_view(
        ...         serializer=PydanticFastSerializer,
        ...     ),
        ... )

    .. warning::

        ``jwt_refresh_cookie_path`` defaults to ``'/'`` here, which sends
        the refresh token with every request to your site. The reusable
        controller has no default on purpose, but a ready-to-use one
        cannot know the url of your refresh endpoint.
        Point it there as soon as you have one, and the refresh token
        stops being sent with anything else:

        .. code:: python

            >>> from django.urls import reverse_lazy
            >>> route = path(
            ...     'login/',
            ...     CookieObtainTokensSyncController.as_view(
            ...         serializer=PydanticFastSerializer,
            ...         jwt_refresh_cookie_path=reverse_lazy('api:refresh'),
            ...     ),
            ... )

        Every controller that shares the cookies has to agree on the value,
        so pass it to the refresh and the logout controller as well.

    See :class:`~dmr.security.jwt.views.CookieObtainTokensSyncController`
    for all the cookie settings and hooks it inherits,
    and subclass that one for any custom logic instead of this controller.

    .. versionadded:: 0.16.0
    """

    # Auth endpoints handle credentials on their own,
    # so auth from the settings must never be required for them:
    auth = None

    jwt_refresh_cookie_path: ClassVar[StrOrPromise | None] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | Sentinel = EMPTY,
        jwt_refresh_cookie_path: StrOrPromise | Sentinel = EMPTY,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with its required fields filled in.

        *serializer* is required, *jwt_refresh_cookie_path* replaces
        the default ``'/'``. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(
            cls,
            serializer=serializer,
            jwt_refresh_cookie_path=jwt_refresh_cookie_path,
        )
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)

    @override
    def convert_auth_payload(
        self,
        payload: views.ObtainTokensPayload,
    ) -> views.ObtainTokensPayload:
        """Default payload is already what ``authenticate`` expects."""
        return payload


@final
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

    # Auth endpoints handle credentials on their own,
    # so auth from the settings must never be required for them:
    auth = None

    jwt_refresh_cookie_path: ClassVar[StrOrPromise | None] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | Sentinel = EMPTY,
        jwt_refresh_cookie_path: StrOrPromise | Sentinel = EMPTY,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with its required fields filled in.

        *serializer* is required, *jwt_refresh_cookie_path* replaces
        the default ``'/'``. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(
            cls,
            serializer=serializer,
            jwt_refresh_cookie_path=jwt_refresh_cookie_path,
        )
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)

    @override
    async def convert_auth_payload(
        self,
        payload: views.ObtainTokensPayload,
    ) -> views.ObtainTokensPayload:
        """Default payload is already what ``aauthenticate`` expects."""
        return payload


@final
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

    # Auth endpoints handle credentials on their own,
    # so auth from the settings must never be required for them:
    auth = None

    jwt_refresh_cookie_path: ClassVar[StrOrPromise | None] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | Sentinel = EMPTY,
        jwt_refresh_cookie_path: StrOrPromise | Sentinel = EMPTY,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with its required fields filled in.

        *serializer* is required, *jwt_refresh_cookie_path* replaces
        the default ``'/'``. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(
            cls,
            serializer=serializer,
            jwt_refresh_cookie_path=jwt_refresh_cookie_path,
        )
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)


@final
class CookieRefreshTokensAsyncController(
    views.CookieRefreshTokensAsyncController[_SerializerT, _CookieResponseT],
):
    """
    Async controller to rotate both token cookies, ready to be routed.

    Async version of
    :class:`~dmr.security.jwt.concrete_views.CookieRefreshTokensSyncController`.

    .. versionadded:: 0.16.0
    """

    # Auth endpoints handle credentials on their own,
    # so auth from the settings must never be required for them:
    auth = None

    jwt_refresh_cookie_path: ClassVar[StrOrPromise | None] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | Sentinel = EMPTY,
        jwt_refresh_cookie_path: StrOrPromise | Sentinel = EMPTY,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with its required fields filled in.

        *serializer* is required, *jwt_refresh_cookie_path* replaces
        the default ``'/'``. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(
            cls,
            serializer=serializer,
            jwt_refresh_cookie_path=jwt_refresh_cookie_path,
        )
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)


@final
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

    # Auth endpoints handle credentials on their own,
    # so auth from the settings must never be required for them:
    auth = None

    jwt_refresh_cookie_path: ClassVar[StrOrPromise | None] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | Sentinel = EMPTY,
        jwt_refresh_cookie_path: StrOrPromise | Sentinel = EMPTY,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with its required fields filled in.

        *serializer* is required, *jwt_refresh_cookie_path* replaces
        the default ``'/'``. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(
            cls,
            serializer=serializer,
            jwt_refresh_cookie_path=jwt_refresh_cookie_path,
        )
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)


@final
class CookieLogoutAsyncController(
    views.CookieLogoutAsyncController[_SerializerT, _CookieResponseT],
):
    """
    Async controller to drop both token cookies, ready to be routed.

    Async version of
    :class:`~dmr.security.jwt.concrete_views.CookieLogoutSyncController`.

    .. versionadded:: 0.16.0
    """

    # Auth endpoints handle credentials on their own,
    # so auth from the settings must never be required for them:
    auth = None

    jwt_refresh_cookie_path: ClassVar[StrOrPromise | None] = (
        DEFAULT_REFRESH_COOKIE_PATH
    )

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | Sentinel = EMPTY,
        jwt_refresh_cookie_path: StrOrPromise | Sentinel = EMPTY,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with its required fields filled in.

        *serializer* is required, *jwt_refresh_cookie_path* replaces
        the default ``'/'``. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(
            cls,
            serializer=serializer,
            jwt_refresh_cookie_path=jwt_refresh_cookie_path,
        )
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)
