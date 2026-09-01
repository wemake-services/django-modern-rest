import dataclasses
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Final, Literal, Self, final, overload

from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.headers import HeaderSpec
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

#: Name of the header that carries auth challenges in ``401`` responses.
WWW_AUTHENTICATE: Final = 'WWW-Authenticate'

#: Returned by auth that has no ``WWW-Authenticate`` challenge to advertise.
NO_CHALLENGE: Final[str | None] = None

_WWW_AUTHENTICATE_SPEC: Final = HeaderSpec(
    description=(
        'Challenges that the client can use to authenticate this request'
    ),
    # A `401` can also be raised by hand from an endpoint body,
    # and then we have no auth instance to build a challenge from.
    # So, we document the header, but never enforce it in runtime.
    skip_validation=True,
)


def unauth_response_spec(
    controller_cls: type['Controller[BaseSerializer]'],
    metadata: EndpointMetadata | None = None,
) -> ResponseSpec:
    """
    Defines the default unauthed response spec.

    When *metadata* is passed and its auth chain can produce
    a ``WWW-Authenticate`` challenge, we also document that header.
    """
    has_challenge = (
        metadata is not None
        and combined_www_authenticate(metadata.auth) is not None
    )
    return ResponseSpec(
        controller_cls.error_model,
        status_code=NotAuthenticatedError.status_code,
        description='Raised when auth was not successful',
        headers=(
            {WWW_AUTHENTICATE: _WWW_AUTHENTICATE_SPEC}
            if has_challenge
            else None
        ),
    )


def combined_www_authenticate(
    auth: Sequence['SyncAuth | AsyncAuth'] | None,
) -> str | None:
    """
    Join ``WWW-Authenticate`` challenges of *auth* into a single header value.

    :rfc:`9110#section-11.6.1` allows a challenge list,
    so an endpoint with several auth instances advertises all of them at once.
    Returns ``None`` when no auth in the chain has a challenge to send.
    """
    if not auth:
        return None
    all_challenges = [single.www_authenticate_challenge for single in auth]
    # `dict.fromkeys` removes duplicates, but keeps the original order:
    challenges = dict.fromkeys(
        challenge for challenge in all_challenges if challenge
    )
    return ', '.join(challenges) or None


class _BaseAuth(ResponseSpecProvider):
    """
    Base class for all auth instances.

    .. note::

        It is really important for this class to have stateless instances.
        Not even locks can be shared, because these instances can
        be global. It is possible to use them in settings or per controller.
        No state allowed.

    """

    __slots__ = ()

    @property
    @abstractmethod
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        raise NotImplementedError

    @property
    @abstractmethod
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        raise NotImplementedError

    @property
    def www_authenticate_challenge(self) -> str | None:
        """
        Challenge to advertise in ``WWW-Authenticate`` on ``401`` responses.

        :rfc:`9110#section-15.5.2` requires every ``401`` to carry at least
        one challenge, but a challenge can only describe an HTTP
        authentication scheme sent in the ``Authorization`` header.
        Auth that reads credentials from a cookie or from a custom header
        has nothing to put here and returns ``None``,
        which is why this is the default implementation.

        Override it to send a challenge of your own.

        .. versionadded:: 0.15.0
        """
        return NO_CHALLENGE

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when user is not authed."""
        return self._add_new_response(
            unauth_response_spec(controller_cls, metadata),
            existing_responses,
        )


class SyncAuth(_BaseAuth):
    """
    Sync auth base class for sync endpoints.

    All auth must support initialization without any required parameters.
    Auth can have non-required parameters with defaults.
    """

    __slots__ = ()

    @abstractmethod
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """
        Put your auth business logic here.

        Return ``self`` if the login attempt was successful.
        Return ``None`` if login attempt failed and we need
        to try another authes.
        Raise :exc:`dmr.exceptions.NotAuthenticatedError`
        to immediately fail the login without trying other authes.
        Raise :exc:`dmr.response.APIError`
        if you want to change the return code, for example,
        when some data is missing or has wrong format.
        """


class AsyncAuth(_BaseAuth):
    """
    Async auth base class for async endpoints.

    All auth must support initialization without any required parameters.
    Auth can have non-required parameters with defaults.
    """

    __slots__ = ()

    @abstractmethod
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """
        Put your auth business logic here.

        Return ``self`` if the login attempt was successful.
        Return ``None`` if login attempt failed and we need
        to try another authes.
        Raise :exc:`dmr.exceptions.NotAuthenticatedError`
        to immediately fail the login without trying other authes.
        Raise :exc:`dmr.response.APIError`
        if you want to change the return code, for example,
        when some data is missing or has wrong format.
        """


@final
@dataclasses.dataclass(slots=True, frozen=True)
class SyncOrAsyncAuth:
    """
    Auth that selects between a sync and async instance.

    Use in global settings to apply a single auth rule to both
    sync and async endpoints. Not allowed on controller or endpoint level.

    .. versionadded:: 0.11.0
    """

    _sync_auth: SyncAuth
    _async_auth: AsyncAuth

    def resolve(
        self,
        auth_cls: type[SyncAuth] | type[AsyncAuth],
    ) -> SyncAuth | AsyncAuth:
        """Return the auth instance matching *auth_cls*."""
        if issubclass(auth_cls, SyncAuth):
            return self._sync_auth
        return self._async_auth


@overload
def request_auth(
    request: HttpRequest,
    *,
    strict: Literal[True],
) -> SyncAuth | AsyncAuth: ...


@overload
def request_auth(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> SyncAuth | AsyncAuth | None: ...


def request_auth(
    request: HttpRequest,
    *,
    strict: bool = False,
) -> SyncAuth | AsyncAuth | None:
    """
    Return the auth instance that was used to auth this request.

    When *strict* is passed and *request* has no auth,
    we raise :exc:`AttributeError`.
    """
    auth = getattr(request, '__dmr_auth__', None)
    if auth is None and strict:
        raise AttributeError('__dmr_auth__')
    return auth
