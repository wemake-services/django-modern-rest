from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, final

from django.conf import settings
from django.http import HttpRequest
from django.middleware.csrf import CsrfViewMiddleware
from typing_extensions import override

from django_modern_rest.exceptions import (
    NotAuthenticatedError,
    PermissionDeniedError,
)
from django_modern_rest.metadata import (
    EndpointMetadata,
    ResponseSpec,
    ResponseSpecProvider,
)
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


@final
class _EnsureCsrfToken(CsrfViewMiddleware):
    """
    CSRF check middleware that returns the rejection reason.

    Used for checking CSRF tokens manually.
    """

    def _reject(self, request: HttpRequest, reason: str) -> str:
        # Return the failure reason instead of an ``HttpResponse``.
        return reason


def _enforce_csrf(request: HttpRequest) -> None:
    """Perform CSRF validation using ``_CheckCSRF``."""
    check = _EnsureCsrfToken(lambda _: None)  # type: ignore[arg-type]
    check.process_request(request)
    reason = check.process_view(request, None, (), {})  # type: ignore[arg-type]
    if reason:
        raise PermissionDeniedError(f'CSRF Failed: {reason}')


class _DjangoSessionAuth(ResponseSpecProvider):
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

    @override
    @classmethod
    def provide_response_specs(
        cls,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when user is not authed."""
        specs: list[ResponseSpec] = []
        specs.extend(
            cls._add_new_response(
                ResponseSpec(
                    controller_cls.error_model,
                    status_code=NotAuthenticatedError.status_code,
                    description='Raised when auth was not successful',
                ),
                existing_responses,
            ),
        )
        specs.extend(
            cls._add_new_response(
                ResponseSpec(
                    controller_cls.error_model,
                    status_code=PermissionDeniedError.status_code,
                    description='Raised when CSRF check failed',
                ),
                existing_responses,
            ),
        )
        return specs


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

    def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        """
        Override this method to provide other authentication logic.

        For example: checking that user is staff / superuser.
        """
        user = getattr(controller.request, 'user', None)
        if not user or not user.is_authenticated or not user.is_active:
            return None

        _enforce_csrf(controller.request)
        return user


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
        return await self.authenticate(endpoint, controller)

    async def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        """
        Override this method to provide other authentication logic.

        For example: checking that user is staff / superuser.
        """
        auser = getattr(controller.request, 'auser', None)
        if auser is None:
            return None
        user = await auser()
        if not user.is_authenticated or not user.is_active:
            return None

        _enforce_csrf(controller.request)
        return user
