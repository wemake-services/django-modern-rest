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

    @property
    @abstractmethod
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""

    def provide_responses(
        self,
        serializer: type['BaseSerializer'],
    ) -> list[ResponseSpec]:
        """
        Provides extra responses.

        Is active when ``enable_semantic_responses`` in endpoint is ``True``.
        """
        return [
            ResponseSpec(
                # We do this for runtime validation, not static type check:
                serializer.default_error_model,
                status_code=NotAuthenticatedError.status_code,
            ),
        ]


class SyncAuth(_BaseAuth):
    """Sync auth base class for sync endpoints."""

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
        Raise :exc:`django.core.exception.PermissionDenied`
        to immediately fail the login without trying other authes.
        Return any other value if the auth succeeded.
        """


class AsyncAuth(_BaseAuth):
    """Async auth base class for async endpoints."""

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
        Raise :exc:`django.core.exception.PermissionDenied`
        to immediately fail the login without trying other authes.
        Return any other value if the auth succeeded.
        """
