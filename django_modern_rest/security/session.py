from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from typing_extensions import override

from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.openapi.objects.security_requirement import (
    SecurityRequirement,
)
from django_modern_rest.openapi.objects.security_scheme import SecurityScheme
from django_modern_rest.security.base import AsyncAuth, SyncAuth

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.serialization import BaseSerializer


class _DjangoSessionAuth:
    __slots__ = ()

    security_scheme_name: ClassVar[str] = 'django_session'

    @property
    def security_scheme(self) -> Components:
        """Provides a security schema definition."""
        return Components(
            security_schemes={
                self.security_scheme_name: SecurityScheme(
                    type='apiKey',
                    name=settings.SESSION_COOKIE_NAME,
                    security_scheme_in='cookie',
                    description='Reusing standard Django auth flow for API',
                ),
            },
        )

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}

    def _authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        if controller.request.user.is_authenticated:
            return controller.request.user
        return None


class DjangoSessionSyncAuth(_DjangoSessionAuth, SyncAuth):
    """
    Reuses Django's regular session auth for the API.

    This class is used for sync endpoints.

    See also:
        https://docs.djangoproject.com/en/6.0/topics/auth/

    """

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        """Does check for the existing request user."""
        return self._authenticate(endpoint, controller)


class DjangoSessionAsyncAuth(_DjangoSessionAuth, AsyncAuth):
    """
    Reuses Django's regular session auth for the API.

    This class is used for async endpoints.

    See also:
        https://docs.djangoproject.com/en/6.0/topics/auth/

    """

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        """Does check for the existing request user."""
        return self._authenticate(endpoint, controller)
