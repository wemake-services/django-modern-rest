from abc import abstractmethod
from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, final

from django.conf import settings
from django.http import HttpRequest
from django.middleware.csrf import CsrfViewMiddleware
from typing_extensions import override

from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security.base import unauth_response_spec
from dmr.security.csrf import (
    SAFE_HTTP_METHODS,
    csrf_message,
    csrf_response_spec,
    csrf_security_scheme,
)
from dmr.semantic_schema import AuthProvider

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer


def ensure_csrf(controller: 'Controller[BaseSerializer]') -> None:
    """
    Raise ``APIError`` (403) if the CSRF check fails.

    Does not perform the second CSRF check if it was processed before.
    Since it uses the standard Django tooling, the default middleware
    checks ``csrf_processing_done`` which is set on each successful check.
    """
    from dmr.response import APIError  # noqa: PLC0415

    reason = _check_csrf_failure(controller.request)

    if reason is not None:
        raise APIError(
            controller.format_error(reason),
            status_code=HTTPStatus.FORBIDDEN,
        )


class CSRFAuthMixin(ResponseSpecProvider, AuthProvider):
    """
    Shared parts of auth classes that are protected by CSRF.

    Auth that reads credentials that browsers send automatically
    (cookies, sessions) must also be protected from CSRF.
    Such auth has to enforce the CSRF check in runtime
    and to document it in the OpenAPI schema:
    an extra security scheme, an extra security requirement
    for unsafe HTTP methods, and the extra ``403`` response.

    This mixin does all of it. Subclasses only have to:

    - set ``security_scheme_name`` and ``csrf_scheme_name`` attributes,
    - implement :meth:`auth_security_scheme` with their own scheme,
    - call ``_ensure_csrf`` from ``__call__`` at the right moment.

    Must be listed before the concrete auth base in the class bases,
    so the methods here win over the default ones.
    """

    __slots__ = ()

    security_scheme_name: str
    csrf_scheme_name: str

    @property
    def www_authenticate_challenge(self) -> str | None:
        """
        This auth has no challenge to advertise, so this returns ``None``.

        A challenge asks the client for the ``Authorization`` header,
        while this auth reads credentials that need CSRF protection instead.
        """

    @abstractmethod
    def auth_security_scheme(self) -> SecurityScheme:
        """Provides the security scheme of the auth itself, without CSRF."""
        raise NotImplementedError

    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, 'SecurityScheme | Reference']:
        """Provides the auth security scheme together with the CSRF one."""
        schemes: dict[str, SecurityScheme | Reference] = {
            self.security_scheme_name: self.auth_security_scheme(),
        }
        # TODO: support `CSRF` checks based on Django sessions
        if self._uses_csrf_cookie():
            schemes[self.csrf_scheme_name] = csrf_security_scheme()
        return schemes

    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[SecurityRequirement]:
        """Requires the auth scheme and CSRF for unsafe HTTP methods."""
        requirement: SecurityRequirement = {self.security_scheme_name: []}
        if self._uses_csrf_cookie() and not self._is_safe_http_method(metadata):
            requirement[self.csrf_scheme_name] = []
        return [requirement]

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Declares extra responses for failed auth and failed CSRF checks."""
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

    def _ensure_csrf(self, controller: 'Controller[BaseSerializer]') -> None:
        """
        Enforce the CSRF check, raise ``APIError`` (403) if it fails.

        Override this to skip the check when the request carries
        no credentials for this auth at all, so the auth chain
        can fall through to the next auth without a CSRF error.
        """
        ensure_csrf(controller)

    def _uses_csrf_cookie(self) -> bool:
        return not settings.CSRF_USE_SESSIONS

    def _is_safe_http_method(self, metadata: EndpointMetadata) -> bool:
        return metadata.method.upper() in SAFE_HTTP_METHODS


@final
class _EnsureCsrfToken(CsrfViewMiddleware):
    """
    CSRF check middleware that returns the rejection reason.

    Used for checking CSRF tokens manually.
    """

    def _reject(self, request: HttpRequest, reason: str) -> str:
        # Return the failure reason instead of an ``HttpResponse``.
        # Expose detailed csrf failure reason on DEBUG mode.
        # Otherwise, provide default placeholder reason.
        return csrf_message(reason)


def _check_csrf_failure(request: HttpRequest) -> str | None:
    """Perform CSRF validation using ``_EnsureCsrfToken``."""
    check = _EnsureCsrfToken(lambda _: None)  # type: ignore[arg-type]
    check.process_request(request)
    return check.process_view(request, None, (), {})  # type: ignore[arg-type, return-value]
