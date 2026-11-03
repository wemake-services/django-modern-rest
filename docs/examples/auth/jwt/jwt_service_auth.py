from typing import Self, Unpack

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


class HeaderPermissionJWTSyncAuth(SyncAuth, BaseJWTokenHandler):  # noqa: WPS214
    """Extract service JWTs from the Authorization header."""

    __slots__ = ('auth_header', 'auth_scheme', 'permission', 'schema_name')

    def __init__(  # noqa: WPS211
        self,
        *,
        permission: str = 'access',
        schema_name: str = 'service_jwt',
        auth_header: str = 'Authorization',
        auth_scheme: str = 'Bearer',
        **kwargs: Unpack[BaseJWTokenHandlerParams],
    ) -> None:
        super().__init__(**kwargs)
        self.permission = permission
        self.schema_name = schema_name
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme

    @override
    @sensitive_variables()
    def __call__(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
    ) -> Self | None:
        token = self.prepare_token(controller.request)
        if token is None:
            return None
        return self

    @override
    def validate_token(self, decoded_token: JWToken) -> JWToken | None:
        if decoded_token.extras.get('permission') != self.permission:
            return None
        return super().validate_token(decoded_token)

    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        return self.auth_scheme

    @override
    def get_token_from_request(self, request: HttpRequest) -> str | None:
        return request.headers.get(self.auth_header)

    @override
    def split_encoded_token(self, header: str) -> str | None:
        try:
            auth_scheme, encoded_token = header.split()
        except ValueError:
            return None

        if auth_scheme != self.auth_scheme:
            return None

        return encoded_token

    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, SecurityScheme | Reference]:
        return {
            self.schema_name: SecurityScheme(
                type='http',
                scheme=self.auth_scheme,
                bearer_format='JWT',
            ),
        }

    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[SecurityRequirement]:
        return [{self.schema_name: []}]


class ServiceController(Controller[PydanticFastSerializer]):
    """Controller using custom JWT authentication."""

    auth = (
        HeaderPermissionJWTSyncAuth(
            permission='report',
            accepted_issuers='VerifyServiceId',
        ),
    )

    def get(self) -> str:
        return 'Authenticated'


# openapi: {"controller": "ServiceController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
