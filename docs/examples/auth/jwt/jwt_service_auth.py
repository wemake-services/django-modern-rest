from typing import Final, Self, Unpack, cast, final

from django.http import HttpRequest
from django.views.decorators.debug import sensitive_variables
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.metadata import EndpointMetadata
from dmr.openapi.objects import (
    Reference,
    SecurityRequirement,
    SecurityScheme,
)
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import SyncAuth
from dmr.security.jwt import JWToken
from dmr.security.jwt.auth.base import (
    BaseJWTokenHandler,
    BaseJWTokenHandlerParams,
)
from dmr.serializer import BaseSerializer


@final
class ServiceRequest(HttpRequest):
    """Request with the authenticated service identifier."""

    service_id: str


class PermissionJWTSyncAuth(SyncAuth, BaseJWTokenHandler):
    """Base JWT authentication class for service permissions."""

    __slots__ = ('permission',)

    def __init__(
        self,
        *,
        permission: str = 'access',
        **kwargs: Unpack[BaseJWTokenHandlerParams],
    ) -> None:
        """Configure the required permission."""
        super().__init__(**kwargs)
        self.permission = permission

    # Override via SyncAuth Contract.
    @override
    @sensitive_variables()
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self | None:
        """Authenticate the service using its JWT."""
        token = self.prepare_token(controller.request)
        if token is None:
            return None

        request = cast(ServiceRequest, controller.request)
        request.service_id = token.sub

        return self

    # Override via BaseJWTokenHandler Contract.
    @override
    def validate_token(self, decoded_token: JWToken) -> JWToken | None:
        """Performs token authorization in accordance with the permission."""
        if decoded_token.extras.get('permission') != self.permission:
            return None
        return super().validate_token(decoded_token)


@final
class HeaderPermissionJWTSyncAuth(PermissionJWTSyncAuth):
    """Extract service JWTs from the Authorization header."""

    __slots__ = ('auth_header', 'auth_scheme', 'schema_name')

    def __init__(  # noqa: WPS211
        self,
        *,
        permission: str = 'access',
        schema_name: str = 'service_jwt',
        auth_header: str = 'Authorization',
        auth_scheme: str = 'Bearer',
        **kwargs: Unpack[BaseJWTokenHandlerParams],
    ) -> None:
        """Configure the HTTP authentication header."""
        super().__init__(permission=permission, **kwargs)
        self.schema_name = schema_name
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme

    # Override via SyncAuth Contract.
    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        """Return the HTTP authentication scheme."""
        return self.auth_scheme

    # Override via BaseJWTokenHandler Contract.
    @override
    def get_token_from_request(self, request: HttpRequest) -> str | None:
        """Extract the raw authentication header."""
        return request.headers.get(self.auth_header)

    # Override via BaseJWTokenHandler Contract.
    @override
    def split_encoded_token(self, header: str) -> str | None:
        """Extract the encoded JWT from the authorization header."""
        try:
            auth_scheme, encoded_token = header.split()
        except ValueError:
            return None

        if auth_scheme != self.auth_scheme:
            return None

        return encoded_token

    # Override via SecurityProvider Contract.
    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, SecurityScheme | Reference]:
        """Describe the service JWT authentication in OpenAPI."""
        return {
            self.schema_name: SecurityScheme(
                type='http',
                scheme=self.auth_scheme,
                bearer_format='JWT',
                description='Service-to-service JWT authentication',
            ),
        }

    # Override via SecurityProvider Contract.
    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[SecurityRequirement]:
        """Require the service JWT authentication scheme."""
        return [{self.schema_name: []}]


ReportSyncAuth: Final = HeaderPermissionJWTSyncAuth(
    permission='report',
    accepted_issuers='VerifyServiceId',
)

DownloadSyncAuth: Final = HeaderPermissionJWTSyncAuth(
    permission='download',
    accepted_issuers='VerifyServiceId',
)


@final
class ServiceController(Controller[PydanticFastSerializer]):
    """Allow services with either report or download permission."""

    request: ServiceRequest
    auth = (ReportSyncAuth, DownloadSyncAuth)

    def get(self) -> str:
        """Return the authenticated service identifier."""
        return self.request.service_id


# openapi: {"controller": "ServiceController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
