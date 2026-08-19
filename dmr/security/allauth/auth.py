from typing import TYPE_CHECKING, Final, Literal, Self, cast, overload

from asgiref.sync import sync_to_async
from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security.base import AsyncAuth, SyncAuth

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.sessions.backends.base import SessionBase

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

#: Header that ``django-allauth`` uses to transfer its session tokens.
DEFAULT_SESSION_TOKEN_HEADER: Final = 'X-Session-Token'  # noqa: S105


class _BaseXSessionTokenAuth:
    """
    Auth for ``django-allauth``'s headless session tokens.

    ``django-allauth`` handles the whole login flow in its headless mode,
    and hands the client a session token. The client then sends that token
    back in the ``X-Session-Token`` header on every API request.
    This class turns that header into an authenticated ``request.user``.

    .. note::

        Tokens are read from a header, never from a cookie,
        so browsers do not attach them automatically
        and no CSRF protection is needed here.

    """

    __slots__ = ('header_name', 'security_scheme_name')

    def __init__(
        self,
        *,
        header_name: str = DEFAULT_SESSION_TOKEN_HEADER,
        security_scheme_name: str = 'session_token',
    ) -> None:
        """Apply possible customizations."""
        self.header_name = header_name
        self.security_scheme_name = security_scheme_name

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.header_name,
                security_scheme_in='header',
                description='`django-allauth` headless session token',
            ),
        }

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}

    def get_session_token(self, request: HttpRequest) -> str | None:
        """
        Return the raw session token for the given request.

        By default we look up the ``X-Session-Token`` header.
        Override this if you want to extract the token from somewhere else,
        for example from the ``Authorization`` header.
        """
        return request.headers.get(self.header_name)


def _authenticate(token: str) -> 'tuple[AbstractBaseUser, SessionBase]':
    # Imported lazily, so this module stays importable
    # without calling `django.setup()` first.
    # `django-allauth` ships no type information, hence the ignores:
    from allauth.headless.internal.sessionkit import (  # noqa: PLC0415  # type: ignore[import-untyped]  # pyright: ignore[reportMissingTypeStubs]
        authenticate_by_x_session_token,  # pyright: ignore[reportUnknownVariableType]
    )

    # `django-allauth` already checks that the user is active,
    # and returns `None` for unknown / expired / anonymous sessions.
    authenticated = cast(
        'tuple[AbstractBaseUser, SessionBase] | None',
        authenticate_by_x_session_token(token),
    )
    if authenticated is None:
        raise NotAuthenticatedError
    return authenticated


class XSessionTokenSyncAuth(_BaseXSessionTokenAuth, SyncAuth):
    """
    Sync auth for ``django-allauth``'s headless session tokens.

    See also:
        https://docs.allauth.org/en/latest/headless/token-strategies/session-tokens.html

    .. versionadded:: 0.15.0
    """

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Does check for the correct session token."""
        token = self.get_session_token(controller.request)
        # We return `None` here, because it might be some other auth.
        # We don't want to falsely trigger any errors just yet.
        if not token:
            return None
        self.authenticate(controller.request, token)
        return self

    def authenticate(
        self,
        request: HttpRequest,
        token: str,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        user, session = _authenticate(token)
        self.set_request_attrs(request, user, session=session)
        return user

    def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        *,
        session: 'SessionBase',
    ) -> None:
        """Set current user as authed for this request."""
        set_request_attrs(request, user, session=session)


class XSessionTokenAsyncAuth(_BaseXSessionTokenAuth, AsyncAuth):
    """
    Async auth for ``django-allauth``'s headless session tokens.

    ``django-allauth`` has no async API, so the session lookup runs
    in a threadpool via ``asgiref.sync.sync_to_async``.

    See also:
        https://docs.allauth.org/en/latest/headless/token-strategies/session-tokens.html

    .. versionadded:: 0.15.0
    """

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Does check for the correct session token."""
        token = self.get_session_token(controller.request)
        # We return `None` here, because it might be some other auth.
        # We don't want to falsely trigger any errors just yet.
        if not token:
            return None
        await self.authenticate(controller.request, token)
        return self

    async def authenticate(
        self,
        request: HttpRequest,
        token: str,
    ) -> 'AbstractBaseUser':
        """Run all auth pipeline."""
        user, session = await sync_to_async(_authenticate)(token)
        await self.set_request_attrs(request, user, session=session)
        return user

    async def set_request_attrs(
        self,
        request: HttpRequest,
        user: 'AbstractBaseUser',
        *,
        session: 'SessionBase',
    ) -> None:
        """Set current user as authed for this request."""
        set_request_attrs(request, user, session=session)


@overload
def request_allauth_session(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> 'SessionBase': ...


@overload
def request_allauth_session(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'SessionBase | None': ...


def request_allauth_session(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> 'SessionBase | None':
    """
    Returns the ``django-allauth`` session, if request was authed with it.

    This is the session that the token was resolved into,
    not :attr:`django.http.HttpRequest.session` of the current request.

    When *strict* is passed and *request* has no such session,
    we raise :exc:`AttributeError`.
    """
    session: SessionBase | None = getattr(
        request,
        '__dmr_allauth_session__',
        None,
    )
    if session is None and strict:
        raise AttributeError('__dmr_allauth_session__')
    return session


def set_request_attrs(
    request: HttpRequest,
    user: 'AbstractBaseUser',
    *,
    session: 'SessionBase | None' = None,
) -> None:
    """Set all required properties to the authed request."""
    request.user = user

    # This is needed even for sync views for consistency,
    # and wild `async_to_sync` / `sync_to_async` use-cases:

    async def auser() -> 'AbstractBaseUser':  # noqa: WPS430
        return user

    request.auser = auser

    if session is not None:
        request.__dmr_allauth_session__ = session  # type: ignore[attr-defined]
