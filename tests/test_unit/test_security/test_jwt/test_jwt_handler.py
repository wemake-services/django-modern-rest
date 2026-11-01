import datetime as dt
from http import HTTPStatus
from typing import Final, Literal, Self, Unpack, final

import pytest
from django.conf import LazySettings
from django.http import HttpRequest
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.metadata import EndpointMetadata
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security import SyncAuth
from dmr.security.jwt import JWToken
from dmr.security.jwt.auth.base import (
    BaseJWTokenHandler,
    BaseJWTokenHandlerParams,
)
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory


class _CustomJWTSyncAuth(SyncAuth, BaseJWTokenHandler):
    """Provides customizable synchronous JWT authentication."""

    def __init__(
        self,
        *,
        schema_name: str,
        auth_header: str = 'Authorization',
        auth_scheme: str = 'Bearer',
        **kwargs: Unpack[BaseJWTokenHandlerParams],
    ) -> None:
        """Initialization."""
        super().__init__(**kwargs)
        self.schema_name = schema_name
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Authenticates a request using a JWT."""
        token = self.prepare_token(controller.request)
        if token is None:
            return None
        return self

    # Override via SyncAuth Contract.
    @property
    @override
    def www_authenticate_challenge(self) -> str | None:
        """Returns the authentication scheme for the WWW-Authenticate header."""
        return self.auth_scheme

    # Override via BaseJWTokenHandler Contract.
    @override
    def get_token_from_request(self, request: HttpRequest) -> str | None:
        """Extracts the authentication header from the request."""
        return request.headers.get(self.auth_header)

    # Override via BaseJWTokenHandler Contract.
    @override
    def split_encoded_token(self, header: str) -> str | None:
        """Extracts the JWT from the authorization header."""
        try:
            auth_scheme, token = header.split(' ')
        except (ValueError, TypeError):
            return None
        if auth_scheme == self.auth_scheme:
            return token
        raise NotImplementedError

    # Override via SecurityProvider Contract.
    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, 'SecurityScheme | Reference']:
        """Provides a security schema definition."""
        return {
            self.schema_name: SecurityScheme(
                type='http',
                scheme=self.auth_scheme,
                bearer_format='JWT',
                description='JWT token auth',
            ),
        }

    # Override via SecurityProvider Contract.
    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list['SecurityRequirement']:
        """Provides a security schema usage requirement."""
        return [{self.schema_name: []}]


def test_controller_validate_token(
    settings: LazySettings,
) -> None:
    """Ensures the default validator returns the decoded token unchanged."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub='sub',
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    auth = _CustomJWTSyncAuth(schema_name='my_schema')

    encoded_token = auth.split_encoded_token(f'Bearer {token}')
    assert encoded_token is not None

    decoded_token = auth.decode_token(encoded_token)
    assert decoded_token is auth.validate_token(decoded_token)


def test_controller_split_token_incorrect_headers(
    settings: LazySettings,
) -> None:
    """Ensures a token without an authorization scheme is rejected."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub='sub',
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    auth = _CustomJWTSyncAuth(schema_name='my_schema')

    encoded_token = auth.split_encoded_token(token)
    assert encoded_token is None


class _DownloadOnlyJWTSyncAuth(_CustomJWTSyncAuth):
    """Needed to test `validate_token` custom rule."""

    @override
    def validate_token(self, decoded_token: JWToken) -> JWToken | None:
        """Accepts tokens with download permission."""
        if 'download' not in decoded_token.extras.get('permission', []):
            return None
        return decoded_token


_DownloadAuth: Final = _DownloadOnlyJWTSyncAuth(schema_name='schema')


@final
class _DownloadController(Controller[PydanticFastSerializer]):
    """Requires a JWT with the download permission."""

    auth = [_DownloadAuth]

    def get(self) -> Literal['Ok']:
        """Returns "Ok" if auth is successful."""
        return 'Ok'


def test_controller_security_schemes() -> None:
    """Ensures the controller exposes the expected JWT security scheme."""
    metadata = _DownloadController.api_endpoints['GET'].metadata

    security_schemes = _DownloadAuth.security_schemes(
        metadata,
        _DownloadController,
    )
    assert security_schemes == {
        'schema': SecurityScheme(
            type='http',
            scheme='Bearer',
            bearer_format='JWT',
            description='JWT token auth',
        ),
    }

    security_requirements = _DownloadAuth.security_requirements(
        metadata,
        _DownloadController,
    )
    assert security_requirements == [{'schema': []}]


@pytest.mark.parametrize(
    ('permissions', 'expected_status'),
    [
        (['download'], HTTPStatus.OK),
        (['upload'], HTTPStatus.UNAUTHORIZED),
        ([], HTTPStatus.UNAUTHORIZED),
    ],
)
def test_controller_with_permissions(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
    *,
    permissions: list[str],
    expected_status: HTTPStatus,
) -> None:
    """Ensures a controller accepts a JWT with the required permission."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub='sub',
        extras={'permission': permissions},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    request = dmr_rf.get(
        path='/',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadController.as_view()(request)

    assert response.status_code == expected_status
