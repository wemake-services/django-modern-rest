from typing import TYPE_CHECKING, Self, TypeGuard

from django.conf import settings
from typing_extensions import override

from dmr.internal.csrf import CSRFAuthMixin
from dmr.openapi.objects import SecurityScheme
from dmr.security.base import AsyncAuth, SyncAuth
from dmr.security.csrf import CSRF_SCHEME_NAME

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class _DjangoSessionAuth(CSRFAuthMixin):
    """Reuses the user that Django's session middleware already resolved."""

    __slots__ = (
        'csrf_scheme_name',
        'security_scheme_name',
    )

    def __init__(
        self,
        security_scheme_name: str = 'django_session',
        csrf_scheme_name: str = CSRF_SCHEME_NAME,
    ) -> None:
        self.security_scheme_name = security_scheme_name
        self.csrf_scheme_name = csrf_scheme_name

    @override
    def auth_security_scheme(self) -> SecurityScheme:
        """Provides a security schema definition."""
        return SecurityScheme(
            type='apiKey',
            name=settings.SESSION_COOKIE_NAME,
            security_scheme_in='cookie',
            description='Reusing standard Django auth flow for API',
        )

    def _is_user_present(
        self,
        user: 'AbstractBaseUser | AnonymousUser | None',
    ) -> TypeGuard['AbstractBaseUser']:
        return user is not None and user.is_authenticated and user.is_active


class DjangoSessionSyncAuth(_DjangoSessionAuth, SyncAuth):
    """
    Reuses Django's regular session auth for the API.

    This class is used for sync endpoints.
    CSRF is automatically enforced before any other actions.

    See also:
        https://docs.djangoproject.com/en/stable/topics/auth/

    .. versionchanged:: 0.16.0
        Fixed how CSRF schema is generated.

    """

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Does check for the existing request user."""
        return self.authenticate(endpoint, controller)

    def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """
        Override this method to provide other authentication logic.

        For example: checking that user is staff / superuser.
        """
        user = getattr(controller.request, 'user', None)
        if not self._is_user_present(user):
            return None
        # It is important that we first can skip auth with no `user`, see #1289
        self._ensure_csrf(controller)
        return self


class DjangoSessionAsyncAuth(_DjangoSessionAuth, AsyncAuth):
    """
    Reuses Django's regular session auth for the API.

    This class is used for async endpoints.
    CSRF is automatically enforced before any other actions.

    See also:
        https://docs.djangoproject.com/en/stable/topics/auth/

    .. versionchanged:: 0.16.0
        Fixed how CSRF schema is generated.

    """

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Does check for the existing request user."""
        return await self.authenticate(endpoint, controller)

    async def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """
        Override this method to provide other authentication logic.

        For example: checking that user is staff / superuser.
        """
        auser = getattr(controller.request, 'auser', None)
        if auser is None:
            return None
        user = await auser()
        if not self._is_user_present(user):
            return None
        # It is important that we first can skip auth with no `user`, see #1289
        self._ensure_csrf(controller)
        return self
