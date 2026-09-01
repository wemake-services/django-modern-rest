from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Self

from django.conf import settings
from typing_extensions import override

from dmr.internal.csrf import ensure_csrf
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security.base import AsyncAuth, SyncAuth, unauth_response_spec

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class _DjangoSessionAuth(ResponseSpecProvider):
    __slots__ = ('csrf_scheme_name', 'security_scheme_name')

    def __init__(
        self,
        security_scheme_name: str = 'django_session',
        csrf_scheme_name: str = 'csrf',
    ) -> None:
        self.security_scheme_name = security_scheme_name
        self.csrf_scheme_name = csrf_scheme_name

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        schemes: dict[str, SecurityScheme | Reference] = {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=settings.SESSION_COOKIE_NAME,
                security_scheme_in='cookie',
                description='Reusing standard Django auth flow for API',
            ),
        }
        if self._uses_csrf_cookie():
            schemes[self.csrf_scheme_name] = SecurityScheme(
                type='apiKey',
                name=settings.CSRF_COOKIE_NAME,
                security_scheme_in='cookie',
                description='CSRF protection',
            )
        return schemes

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        requirement: SecurityRequirement = {self.security_scheme_name: []}
        if self._uses_csrf_cookie():
            requirement[self.csrf_scheme_name] = []
        return requirement

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when user is not authed."""
        return [
            *self._add_new_response(
                unauth_response_spec(controller_cls, metadata),
                existing_responses,
            ),
            *self._add_new_response(
                ResponseSpec(
                    controller_cls.error_model,
                    status_code=HTTPStatus.FORBIDDEN,
                    description='Raised when CSRF check failed',
                ),
                existing_responses,
            ),
        ]

    def _uses_csrf_cookie(self) -> bool:
        return not settings.CSRF_USE_SESSIONS

    def _is_user_present(
        self,
        user: 'AbstractBaseUser | AnonymousUser | None',
    ) -> bool:
        return user is not None and user.is_authenticated and user.is_active

    def _ensure_csrf(self, controller: 'Controller[BaseSerializer]') -> None:
        ensure_csrf(controller)


class DjangoSessionSyncAuth(_DjangoSessionAuth, SyncAuth):
    """
    Reuses Django's regular session auth for the API.

    This class is used for sync endpoints.

    See also:
        https://docs.djangoproject.com/en/stable/topics/auth/

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

    See also:
        https://docs.djangoproject.com/en/stable/topics/auth/

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
