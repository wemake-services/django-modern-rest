import datetime as dt
import uuid
from http import HTTPStatus
from typing import Literal, Self, Unpack

from django.conf import LazySettings
from django.http import HttpRequest
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.metadata import EndpointMetadata
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.security import SyncAuth, request_auth
from dmr.security.jwt import JWToken
from dmr.security.jwt.auth.base import JWTokenAuthParams, JWTokenHandler
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory

SUB_ID = uuid.UUID('01a17839-3cd1-70e4-851b-66a1fd5d5f1b')
ISS_ID = uuid.UUID('01a17839-639f-70fb-a2b4-346fef040385')


class _CustomJWTSyncAuth(SyncAuth, JWTokenHandler):
    """Provides customizable synchronous JWT authentication."""

    def __init__(
        self,
        *,
        schema_name: str,
        auth_header: str = 'Authorization',
        auth_scheme: str = 'Bearer',
        **kwargs: Unpack[JWTokenAuthParams],
    ) -> None:
        """Initialization."""
        super().__init__(**kwargs)  # pyrefly: ignore[open-unpacking]
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

    # Override via JWTokenHandler Contract.
    @override
    def get_token_from_request(self, request: HttpRequest) -> str | None:
        """Extracts the authentication header from the request."""
        return request.headers.get(self.auth_header)

    # Override via JWTokenHandler Contract.
    @override
    def split_encoded_token(self, header: str) -> str | None:
        """Extracts the JWT from the authorization header."""
        try:
            auth_scheme, token = header.split(' ')
        except (ValueError, TypeError):
            return None
        if auth_scheme == self.auth_scheme:
            return token
        return None

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


class _DownloadOnlyJWTSyncAuth(_CustomJWTSyncAuth):
    """Authenticates JWTs with download permission."""

    @override
    def validate_token(self, decoded_token: JWToken) -> JWToken | None:
        """Accepts tokens with download permission."""
        if 'download' not in decoded_token.extras.get('permission', []):
            return None
        return decoded_token


class _UploadOnlyJWTSyncAuth(_CustomJWTSyncAuth):
    """Authenticates JWTs with upload permission."""

    @override
    def validate_token(self, decoded_token: JWToken) -> JWToken | None:
        """Accepts tokens with upload permission."""
        if 'upload' not in decoded_token.extras.get('permission', []):
            return None
        return decoded_token


class _DownloadOnlyWithIssJWTSyncAuth(_DownloadOnlyJWTSyncAuth):
    """Authenticates JWTs with download permission id issuer."""

    @override
    def validate_token(self, decoded_token: JWToken) -> JWToken | None:
        """Accepts download tokens issued by the expected issuer."""
        token = super().validate_token(decoded_token)
        if token is None:
            return None
        if decoded_token.iss != str(ISS_ID):
            return None
        return token


_DownloadAuth = _DownloadOnlyJWTSyncAuth(schema_name='schema')
_UploadAuth = _UploadOnlyJWTSyncAuth(schema_name='schema')
_DownloadIssAuth = _DownloadOnlyWithIssJWTSyncAuth(schema_name='schema')


class _DownloadController(Controller[MsgspecSerializer]):
    """Requires a JWT with the download permission."""

    auth = [_DownloadAuth]

    def get(self) -> Literal['Ok']:
        """Returns "Ok" if auth is successful."""
        return 'Ok'


class _DownloadIssController(Controller[MsgspecSerializer]):
    """Tests JWT authentication with issuer validation."""

    auth = [_DownloadIssAuth]

    def get(self) -> Literal['Ok']:
        """Returns "Ok" if auth is successful."""
        return 'Ok'


class _DownloadOrUploadController(Controller[MsgspecSerializer]):
    """Accepts JWTs with either download or upload permission."""

    auth = [_UploadAuth, _DownloadAuth]

    def get(self) -> Literal['Ok']:
        """Returns "Ok" if auth is successful."""
        return 'Ok'


def test_controller_security_schemes() -> None:
    """Ensures the controller exposes the expected JWT security scheme."""
    schema_name = 'schema'
    auth_scheme = 'Bearer'
    auth_cls = _CustomJWTSyncAuth(
        schema_name=schema_name,
        auth_scheme=auth_scheme,
    )
    metadata = _DownloadController.api_endpoints['GET'].metadata
    security_schemes = auth_cls.security_schemes(
        metadata,
        _DownloadController,
    )
    assert security_schemes == {
        schema_name: SecurityScheme(
            type='http',
            scheme=auth_scheme,
            bearer_format='JWT',
            description='JWT token auth',
        ),
    }


def test_controller_security_requirements() -> None:
    """Ensures the controller declares the expected JWT security requirement."""
    schema_name = 'my_schema'
    auth_cls = _CustomJWTSyncAuth(schema_name=schema_name)
    metadata = _DownloadController.api_endpoints['GET'].metadata
    security_requirements = auth_cls.security_requirements(
        metadata,
        _DownloadController,
    )
    assert security_requirements == [{schema_name: []}]


def test_controller_validate_token(
    settings: LazySettings,
) -> None:
    """Ensures the default validator returns the decoded token unchanged."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    auth_cls = _CustomJWTSyncAuth(schema_name='my_schema')
    encoded_token = auth_cls.split_encoded_token(f'Bearer {token}')
    assert encoded_token is not None
    decoded_token = auth_cls.decode_token(encoded_token)
    assert decoded_token is auth_cls.validate_token(decoded_token)


def test_controller_split_token_incorrect_headers(
    settings: LazySettings,
) -> None:
    """Ensures a token without an authorization scheme is rejected."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    auth_cls = _CustomJWTSyncAuth(schema_name='my_schema')
    encoded_token = auth_cls.split_encoded_token(token)
    assert encoded_token is None


def test_controller_with_correct_permissions(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures a controller accepts a JWT with the required permission."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
        extras={'permission': ['download']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadController.as_view()(request)
    assert response.status_code == HTTPStatus.OK


def test_controller_with_incorrect_permissions(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures a controller rejects a JWT without the required permission."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
        extras={'permission': ['upload']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadController.as_view()(request)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_controller_with_expired_token(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures a controller rejects an expired JWT."""
    second_delta = 0.25
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) - dt.timedelta(seconds=second_delta),
        sub=str(SUB_ID),
        extras={'permission': ['download']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadController.as_view()(request)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_controller_with_expected_issuer(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures a controller accepts a JWT from the expected issuer."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
        iss=str(ISS_ID),
        extras={'permission': ['download']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadIssController.as_view()(request)
    assert response.status_code == HTTPStatus.OK


def test_iss_controller_without_issuer(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures a controller rejects a JWT without the expected issuer."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
        extras={'permission': ['download']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadIssController.as_view()(request)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_iss_controller_with_incorrect_perms(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures a controller rejects a JWT without the required permission."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
        iss=str(ISS_ID),
        extras={'permission': ['upload']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadIssController.as_view()(request)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_upload_auth_selected(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures the authentication chain accepts a JWT via _UploadAuth."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
        extras={'permission': ['upload']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadOrUploadController.as_view()(request)
    assert response.status_code == HTTPStatus.OK
    assert request_auth(request) is _UploadAuth


def test_download_auth_fallback(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures the authentication chain falls back to _DownloadAuth."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
        extras={'permission': ['download']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Bearer {token}'},
    )
    response = _DownloadOrUploadController.as_view()(request)
    assert response.status_code == HTTPStatus.OK
    assert request_auth(request) is _DownloadAuth


def test_controller_with_incorrect_headers(
    dmr_rf: DMRRequestFactory,
    settings: LazySettings,
) -> None:
    """Ensures the auth chain rejects an unsupported authorization scheme."""
    token = JWToken(
        exp=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
        sub=str(SUB_ID),
        extras={'permission': ['download']},
    ).encode(secret=settings.SECRET_KEY, algorithm='HS256')
    request = dmr_rf.get(
        path='',
        headers={'Authorization': f'Key {token}'},
    )
    response = _DownloadOrUploadController.as_view()(request)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
