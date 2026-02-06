from typing import TYPE_CHECKING, Any

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
    from django_modern_rest.serializer import BaseSerializer


class _DjangoSessionAuth:
    __slots__ = ('security_scheme_name',)

    def __init__(self, security_scheme_name: str = 'django_session') -> None:
        self.security_scheme_name = security_scheme_name

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

    def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        """
        Override this method to provide other authentication logic.

        For example: checking that user is staff / superuser.
        """
        # It is always sync, because no IO ever happens here.
        user = controller.request.user
        if user.is_authenticated and user.is_active:
            return user
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
        return self.authenticate(endpoint, controller)


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
        return self.authenticate(endpoint, controller)
