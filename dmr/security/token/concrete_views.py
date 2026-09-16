"""
Ready-to-use versions of everything in ``dmr.security.token.views``.

Every controller here is the same controller as the one
with the same name in ``dmr.security.token.views``,
with the default request and response bodies already plugged in.
Only ``token_cls`` is left to you, there is no way to guess
which model holds your tokens.
"""

from typing import Generic, cast

from django.contrib.auth.base_user import AbstractBaseUser
from typing_extensions import TypeVar, override

from dmr.security.token import views
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)
_UserT = TypeVar('_UserT', bound=AbstractBaseUser, default=AbstractBaseUser)


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
    Sync controller to issue an opaque token, almost ready to be routed.

    Takes :class:`~dmr.security.token.views.ObtainTokenPayload`
    and returns :class:`~dmr.security.token.views.ObtainTokenResponse`.

    ``token_cls`` is still required, it is the model
    that stores your tokens:

    .. code:: python

        class ObtainToken(ObtainTokenSyncController[PydanticSerializer]):
            token_cls = Token

    See :class:`~dmr.security.token.views.ObtainTokenSyncController`
    for all the token settings and hooks it inherits,
    switch to it when the default request or response body does not fit.

    .. versionadded:: 0.16.0
    """

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
    Async controller to issue an opaque token, almost ready to be routed.

    Async version of
    :class:`~dmr.security.token.concrete_views.ObtainTokenSyncController`.

    .. versionadded:: 0.16.0
    """

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
