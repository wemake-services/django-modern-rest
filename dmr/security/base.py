from abc import abstractmethod
from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Literal, Self, overload

from django.http import HttpRequest
from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class _BaseAuth(ResponseSpecProvider):
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

    @override
    @classmethod
    def provide_response_specs(
        cls,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when user is not authed."""
        return cls._add_new_response(
            ResponseSpec(
                controller_cls.error_model,
                status_code=NotAuthenticatedError.status_code,
                description='Raised when auth was not successful',
            ),
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

        Return ``None`` if login attempt failed and we need
        to try another authes.
        Raise :exc:`django.core.exceptions.PermissionDenied`
        to immediately fail the login without trying other authes.
        Raise :exc:`dmr.response.APIError`
        if you want to change the return code, for example,
        when some data is missing or has wrong format.
        Return any other value if the auth succeeded.
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

        Return ``None`` if login attempt failed and we need
        to try another authes.
        Raise :exc:`django.core.exceptions.PermissionDenied`
        to immediately fail the login without trying other authes.
        Raise :exc:`dmr.response.APIError`
        if you want to change the return code, for example,
        when some data is missing or has wrong format.
        Return any other value if the auth succeeded.
        """


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
