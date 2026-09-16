import datetime as dt
from typing import Any

from typing_extensions import TypeVar, override

from dmr.security.jwt import views
from dmr.security.jwt.views.base import BaseTokenController
from dmr.serializer import BaseSerializer

_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)


def _issue_token_pair(
    controller: BaseTokenController[Any],
) -> views.ObtainTokensResponse:
    """Issue a fresh pair of access and refresh tokens for the current user."""
    now = dt.datetime.now(dt.UTC)
    return {
        'access_token': controller.create_jwt_token(
            expiration=now + controller.jwt_expiration,
            token_type='access',  # noqa: S106
        ),
        'refresh_token': controller.create_jwt_token(
            expiration=now + controller.jwt_refresh_expiration,
            token_type='refresh',  # noqa: S106
        ),
    }


class ObtainTokensSyncController(
    views.ObtainTokensSyncController[
        _SerializerT,
        views.ObtainTokensPayload,
        views.ObtainTokensResponse,
    ],
):
    """
    Sync controller to get access and refresh tokens, ready to be routed.

    Takes :class:`~dmr.security.jwt.views.ObtainTokensPayload`
    and returns :class:`~dmr.security.jwt.views.ObtainTokensResponse`.
    The only thing it needs is a serializer type:

    .. code:: python

        class ObtainTokens(ObtainTokensSyncController[PydanticSerializer]):
            ...  # nothing else to define

    See :class:`~dmr.security.jwt.views.ObtainTokensSyncController`
    for all the jwt settings and hooks it inherits,
    switch to it when the default request or response body does not fit.

    .. versionadded:: 0.16.0
    """

    @override
    def convert_auth_payload(
        self,
        payload: views.ObtainTokensPayload,
    ) -> views.ObtainTokensPayload:
        """Default payload is already what ``authenticate`` expects."""
        return payload

    @override
    def make_api_response(self) -> views.ObtainTokensResponse:
        """Return a fresh pair of access and refresh tokens."""
        return _issue_token_pair(self)


class ObtainTokensAsyncController(
    views.ObtainTokensAsyncController[
        _SerializerT,
        views.ObtainTokensPayload,
        views.ObtainTokensResponse,
    ],
):
    """
    Async controller to get access and refresh tokens, ready to be routed.

    Async version
    of :class:`~dmr.security.jwt.concrete_views.ObtainTokensSyncController`.

    .. versionadded:: 0.16.0
    """

    @override
    async def convert_auth_payload(
        self,
        payload: views.ObtainTokensPayload,
    ) -> views.ObtainTokensPayload:
        """Default payload is already what ``aauthenticate`` expects."""
        return payload

    @override
    async def make_api_response(self) -> views.ObtainTokensResponse:
        """Return a fresh pair of access and refresh tokens."""
        return _issue_token_pair(self)


class RefreshTokenSyncController(
    views.RefreshTokenSyncController[
        _SerializerT,
        views.RefreshTokenPayload,
        views.ObtainTokensResponse,
    ],
):
    """
    Sync controller to refresh both tokens, ready to be routed.

    Takes :class:`~dmr.security.jwt.views.RefreshTokenPayload`
    and returns :class:`~dmr.security.jwt.views.ObtainTokensResponse`,
    so it is a drop-in pair
    for :class:`~dmr.security.jwt.concrete_views.ObtainTokensSyncController`.

    See :class:`~dmr.security.jwt.views.RefreshTokenSyncController`
    for all the settings and hooks it inherits.

    .. versionadded:: 0.16.0
    """

    @override
    def convert_refresh_payload(
        self,
        payload: views.RefreshTokenPayload,
    ) -> str:
        """Read the refresh token from the default payload."""
        return payload['refresh_token']

    @override
    def make_api_response(self) -> views.ObtainTokensResponse:
        """Return a fresh pair of access and refresh tokens."""
        return _issue_token_pair(self)


class RefreshTokenAsyncController(
    views.RefreshTokenAsyncController[
        _SerializerT,
        views.RefreshTokenPayload,
        views.ObtainTokensResponse,
    ],
):
    """
    Async controller to refresh both tokens, ready to be routed.

    Async version
    of :class:`~dmr.security.jwt.concrete_views.RefreshTokenSyncController`.

    .. versionadded:: 0.16.0
    """

    @override
    async def convert_refresh_payload(
        self,
        payload: views.RefreshTokenPayload,
    ) -> str:
        """Read the refresh token from the default payload."""
        return payload['refresh_token']

    @override
    async def make_api_response(self) -> views.ObtainTokensResponse:
        """Return a fresh pair of access and refresh tokens."""
        return _issue_token_pair(self)


class VerifyTokenSyncController(
    views.VerifyTokenSyncController[
        _SerializerT,
        views.VerifyTokenPayload,
    ],
):
    """
    Sync controller to verify an access token, ready to be routed.

    Takes :class:`~dmr.security.jwt.views.VerifyTokenPayload`
    and answers with an empty ``204 No Content`` when the token is valid.

    See :class:`~dmr.security.jwt.views.VerifyTokenSyncController`
    for all the settings and hooks it inherits.

    .. versionadded:: 0.16.0
    """

    @override
    def convert_verify_payload(self, payload: views.VerifyTokenPayload) -> str:
        """Read the access token from the default payload."""
        return payload['access_token']


class VerifyTokenAsyncController(
    views.VerifyTokenAsyncController[
        _SerializerT,
        views.VerifyTokenPayload,
    ],
):
    """
    Async controller to verify an access token, ready to be routed.

    Async version
    of :class:`~dmr.security.jwt.concrete_views.VerifyTokenSyncController`.

    .. versionadded:: 0.16.0
    """

    @override
    async def convert_verify_payload(
        self,
        payload: views.VerifyTokenPayload,
    ) -> str:
        """Read the access token from the default payload."""
        return payload['access_token']
