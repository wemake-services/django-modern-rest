from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from django_modern_rest.exceptions import NotAuthenticatedError
from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.openapi.objects.security_requirement import (
    SecurityRequirement,
)
from django_modern_rest.response import ResponseSpec

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.serialization import BaseSerializer


class _BaseAuth:
    __slots__ = ()

    @property
    @abstractmethod
    def security_scheme(self) -> Components:
        """Provides a security schema definition."""
        raise NotImplementedError

    @property
    @abstractmethod
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        raise NotImplementedError

    def provide_responses(
        self,
        serializer: type['BaseSerializer'],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when user is not authed."""
        return [
            ResponseSpec(
                # We do this for runtime validation, not static type check:
                serializer.default_error_model,
                status_code=NotAuthenticatedError.status_code,
            ),
        ]


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
    ) -> Any | None:
        """
        Put your auth business logic here.

        Return ``None`` if login attempt failed and we need
        to try another authes.
        Raise :exc:`django.core.exceptions.PermissionDenied`
        to immediately fail the login without trying other authes.
        Raise :exc:`django_modern_rest.response.APIError`
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
    ) -> Any | None:
        """
        Put your auth business logic here.

        Return ``None`` if login attempt failed and we need
        to try another authes.
        Raise :exc:`django.core.exceptions.PermissionDenied`
        to immediately fail the login without trying other authes.
        Raise :exc:`django_modern_rest.response.APIError`
        if you want to change the return code, for example,
        when some data is missing or has wrong format.
        Return any other value if the auth succeeded.
        """
