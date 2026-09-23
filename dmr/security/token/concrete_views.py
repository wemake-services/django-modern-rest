"""
Ready-to-use versions of everything in ``dmr.security.token.views``.

Every controller here is the same controller as the one
with the same name in ``dmr.security.token.views``,
with the default request and response bodies already plugged in
and ``token_cls`` defaulting to the model of the bundled token app.
"""

import importlib
from collections.abc import Callable
from typing import Any, Generic, cast

from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpResponseBase
from typing_extensions import TypeVar, override

from dmr.internal.concrete import build_concrete_controller
from dmr.security.token import views
from dmr.security.token.token import TokenLikeAsync, TokenLikeSync
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)
_UserT = TypeVar('_UserT', bound=AbstractBaseUser, default=AbstractBaseUser)


def _load_default_model() -> Any:
    # This is needed, so we can trick the `import-linter`
    # that these two modules are independent. This is the only
    # place where they can really interact.
    return importlib.import_module('dmr.security.token.app.models').Token


def _set_default_token_cls(controller: type[Any]) -> None:
    """
    Fill ``token_cls`` of a subclass that did not set one.

    The import happens here and not at module level on purpose:
    ``'dmr.security.token.app'`` is optional, and projects that swap
    the token model must be able to import this module without it.
    """
    if getattr(controller, 'token_cls', None) is None:
        controller.token_cls = _load_default_model()


class ObtainTokenSyncController(
    views.ObtainTokenSyncController[
        _SerializerT,
        views.ObtainTokenPayload,
        views.ObtainTokenResponse,
        _UserT,
    ],
    Generic[_SerializerT, _UserT],
):
    """
    Sync controller to issue an opaque token, ready to be routed.

    Takes :class:`~dmr.security.token.views.ObtainTokenPayload`
    and returns :class:`~dmr.security.token.views.ObtainTokenResponse`.
    ``token_cls`` defaults to
    :class:`~dmr.security.token.app.models.Token`, so the only thing
    it needs is a serializer type:

    .. code:: python

        path('login/', ObtainTokenSyncController.as_view(
            serializer=PydanticSerializer,
        ))

    Pass ``token_cls`` to :meth:`as_view` when you swap the token model,
    see :ref:`swapping-token-model`. The default is imported the first time
    a subclass is built, so projects with their own model
    do not need ``'dmr.security.token.app'`` installed.

    See :class:`~dmr.security.token.views.ObtainTokenSyncController`
    for all the token settings and hooks it inherits,
    switch to it when the default request or response body does not fit.

    .. versionadded:: 0.16.0
    """

    @override
    def __init_subclass__(cls) -> None:
        """Fall back to the token model of the bundled app."""
        _set_default_token_cls(cls)
        super().__init_subclass__()

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | None = None,
        token_cls: type[TokenLikeSync[_UserT]] | None = None,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with its required fields filled in.

        *serializer* is required, unless a subclass already passed one
        as a type argument. *token_cls* replaces the bundled ``Token``
        model. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(
            cls,
            serializer=serializer,
            token_cls=token_cls,
        )
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)

    @override
    def convert_auth_payload(
        self,
        payload: views.ObtainTokenPayload,
    ) -> views.ObtainTokenPayload:
        """Default payload is already what ``authenticate`` expects."""
        return payload

    @override
    def make_api_response(self) -> views.ObtainTokenResponse:
        """Issue a new token for the user we have just authenticated."""
        # `login` has authed this request before calling us,
        # so `request.user` is the real user, not an `AnonymousUser`.
        return {
            'token': self.issue_token(user=cast('_UserT', self.request.user)),
        }


class ObtainTokenAsyncController(
    views.ObtainTokenAsyncController[
        _SerializerT,
        views.ObtainTokenPayload,
        views.ObtainTokenResponse,
        _UserT,
    ],
    Generic[_SerializerT, _UserT],
):
    """
    Async controller to issue an opaque token, ready to be routed.

    Async version of
    :class:`~dmr.security.token.concrete_views.ObtainTokenSyncController`.

    .. versionadded:: 0.16.0
    """

    @override
    def __init_subclass__(cls) -> None:
        """Fall back to the token model of the bundled app."""
        _set_default_token_cls(cls)
        super().__init_subclass__()

    @override
    @classmethod
    def as_view(
        cls,
        *,
        serializer: type[BaseSerializer] | None = None,
        token_cls: type[TokenLikeAsync[_UserT]] | None = None,
        **initkwargs: Any,
    ) -> Callable[..., HttpResponseBase]:
        """
        Route this controller with its required fields filled in.

        *serializer* is required, unless a subclass already passed one
        as a type argument. *token_cls* replaces the bundled ``Token``
        model. *initkwargs* go to django as usual.
        """
        concrete_cls = build_concrete_controller(
            cls,
            serializer=serializer,
            token_cls=token_cls,
        )
        if concrete_cls is None:
            return super().as_view(**initkwargs)
        return concrete_cls.as_view(**initkwargs)

    @override
    async def convert_auth_payload(
        self,
        payload: views.ObtainTokenPayload,
    ) -> views.ObtainTokenPayload:
        """Default payload is already what ``aauthenticate`` expects."""
        return payload

    @override
    async def make_api_response(self) -> views.ObtainTokenResponse:
        """Issue a new token for the user we have just authenticated."""
        # `login` has authed this request before calling us,
        # so `request.user` is the real user, not an `AnonymousUser`.
        user = cast('_UserT', await self.request.auser())
        return {'token': await self.issue_token(user=user)}
