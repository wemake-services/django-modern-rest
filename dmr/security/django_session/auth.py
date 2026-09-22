from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Self, TypeGuard

from django.conf import settings
from typing_extensions import override

from dmr.internal.csrf import ensure_csrf
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security.base import AsyncAuth, SyncAuth, unauth_response_spec
from dmr.security.csrf import (
    CSRF_SCHEME_NAME,
    SAFE_HTTP_METHODS,
    csrf_response_spec,
    csrf_security_scheme,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer


class _DjangoSessionAuth(ResponseSpecProvider):  # noqa: WPS214
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

    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, 'SecurityScheme | Reference']:
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
            schemes[self.csrf_scheme_name] = csrf_security_scheme()
        return schemes

    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[SecurityRequirement]:
        """Provides a security schema usage requirement."""
        requirement: SecurityRequirement = {self.security_scheme_name: []}
        if self._uses_csrf_cookie() and not self._is_safe_http_method(metadata):
            requirement[self.csrf_scheme_name] = []
        return [requirement]

    @property
    def www_authenticate_challenge(self) -> str | None:
        """
        Session auth has no challenge to advertise, so this returns ``None``.

        A challenge asks the client for the ``Authorization`` header,
        and this auth reads the session cookie instead.
        """

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when user is not authed."""
        auth_response = self._add_new_response(
            unauth_response_spec(controller_cls, metadata),
            existing_responses,
        )
        if self._is_safe_http_method(metadata):
            # CSRF errors can't happen for safe methods:
            return auth_response
        return [
            *auth_response,
            *self._add_new_response(
                csrf_response_spec(return_type=controller_cls.error_model),
                existing_responses,
            ),
        ]

    # TODO: refactor this to be a mixin type, it is repeated several times
    def _uses_csrf_cookie(self) -> bool:
        return not settings.CSRF_USE_SESSIONS

    def _is_safe_http_method(self, metadata: EndpointMetadata) -> bool:
        return metadata.method.upper() in SAFE_HTTP_METHODS

    def _is_user_present(
        self,
        user: 'AbstractBaseUser | AnonymousUser | None',
    ) -> TypeGuard['AbstractBaseUser']:
        return user is not None and user.is_authenticated and user.is_active

    def _ensure_csrf(self, controller: 'Controller[BaseSerializer]') -> None:
        ensure_csrf(controller)


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
