from collections.abc import Sequence
from typing import Final, TypeAlias

from django.http import HttpRequest

from dmr.openapi.objects import Reference, SecurityScheme
from dmr.security.jwt.auth.base import BaseJWTAsyncAuth, BaseJWTSyncAuth
from dmr.security.jwt.token import JWToken

# The only header that a `WWW-Authenticate` challenge can ask the client for,
# and the only one that OpenAPI can describe as `type: http`:
_AUTHORIZATION_HEADER: Final = 'Authorization'


class _HeaderJWTAuth:
    """Reads jwt tokens from a request header."""

    # Slots are declared on the concrete classes below,
    # otherwise we get a layout conflict when mixing them in.
    __slots__ = ()

    auth_header: str
    auth_scheme: str
    security_scheme_name: str
    www_authenticate: bool

    @property
    def www_authenticate_challenge(self) -> str | None:
        """
        Challenge naming the scheme this auth expects, like ``Bearer``.

        Returns ``None`` for a custom *auth_header*, because a challenge
        can only ask the client for the ``Authorization`` header.
        ``realm`` is optional for bearer tokens, see :rfc:`6750#section-3`,
        and we don't send it.
        """
        if (
            not self.www_authenticate
            or not self.auth_scheme
            or self.auth_header != _AUTHORIZATION_HEADER
        ):
            return None
        return self.auth_scheme

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        if self._uses_standard_http_bearer_auth():
            return {
                self.security_scheme_name: SecurityScheme(
                    type='http',
                    scheme=self.auth_scheme,
                    bearer_format='JWT',
                    description='JWT token auth',
                ),
            }

        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.auth_header,
                security_scheme_in='header',
                description=self._get_custom_security_scheme_description(),
            ),
        }

    def get_token_from_request(self, request: HttpRequest) -> str | None:
        """Gets the jwt token from the request header."""
        return request.headers.get(self.auth_header)

    def split_encoded_token(self, header: str) -> str | None:
        """Splits string like 'Bearer token' and returns 'token' part."""
        parts = header.split(' ')
        if len(parts) != 2 or parts[0] != self.auth_scheme:
            return None
        return parts[1]

    def _uses_standard_http_bearer_auth(self) -> bool:
        """Whether the auth contract matches OpenAPI HTTP bearer auth."""
        return (
            self.auth_header == _AUTHORIZATION_HEADER
            and self.auth_scheme.casefold() == 'bearer'
        )

    def _get_custom_security_scheme_description(self) -> str:
        """Describe non-standard JWT auth contracts for generated docs."""
        return (
            'JWT token auth via '
            f'`{self.auth_header}` header using '
            f'`{self.auth_scheme} <token>` format'
        )


class HeaderJWTSyncAuth(_HeaderJWTAuth, BaseJWTSyncAuth):
    """
    Sync jwt auth reading the token from a header.

    Defaults to ``Authorization: Bearer <token>``.

    .. versionadded:: 0.15.0

        Previously known as ``JWTSyncAuth``, which is still
        available as an alias.

    """

    __slots__ = ('auth_header', 'auth_scheme', 'www_authenticate')

    def __init__(  # noqa: WPS211
        self,
        *,
        auth_header: str = 'Authorization',
        auth_scheme: str = 'Bearer',
        www_authenticate: bool = True,
        user_id_field: str = 'pk',
        algorithm: str = 'HS256',
        security_scheme_name: str = 'jwt',
        secret: str | None = None,
        token_cls: type[JWToken] = JWToken,
        leeway: int = 0,  # seconds
        accepted_audiences: str | Sequence[str] | None = None,
        accepted_issuers: str | Sequence[str] | None = None,
        require_claims: Sequence[str] | None = None,
        verify_expiry: bool = True,
        verify_issued_at: bool = True,
        verify_jwt_id: bool = True,
        verify_not_before: bool = True,
        verify_subject: bool = True,
        strict_audience: bool = False,
        enforce_minimum_key_length: bool = True,
    ) -> None:
        """
        Apply possible customizations.

        On top of the regular jwt settings, *auth_header* selects
        the header to read, and *auth_scheme* is the prefix
        that the header value must start with.
        *www_authenticate* controls whether ``401`` responses advertise
        this auth in the ``WWW-Authenticate`` header.
        """
        super().__init__(
            user_id_field=user_id_field,
            algorithm=algorithm,
            security_scheme_name=security_scheme_name,
            secret=secret,
            token_cls=token_cls,
            leeway=leeway,
            accepted_audiences=accepted_audiences,
            accepted_issuers=accepted_issuers,
            require_claims=require_claims,
            verify_expiry=verify_expiry,
            verify_issued_at=verify_issued_at,
            verify_jwt_id=verify_jwt_id,
            verify_not_before=verify_not_before,
            verify_subject=verify_subject,
            strict_audience=strict_audience,
            enforce_minimum_key_length=enforce_minimum_key_length,
        )
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme
        self.www_authenticate = www_authenticate


class HeaderJWTAsyncAuth(_HeaderJWTAuth, BaseJWTAsyncAuth):
    """
    Async jwt auth reading the token from a header.

    Defaults to ``Authorization: Bearer <token>``.

    .. versionadded:: 0.15.0

        Previously known as ``JWTAsyncAuth``, which is still
        available as an alias.

    """

    __slots__ = ('auth_header', 'auth_scheme', 'www_authenticate')

    def __init__(  # noqa: WPS211
        self,
        *,
        auth_header: str = 'Authorization',
        auth_scheme: str = 'Bearer',
        www_authenticate: bool = True,
        user_id_field: str = 'pk',
        algorithm: str = 'HS256',
        security_scheme_name: str = 'jwt',
        secret: str | None = None,
        token_cls: type[JWToken] = JWToken,
        leeway: int = 0,  # seconds
        accepted_audiences: str | Sequence[str] | None = None,
        accepted_issuers: str | Sequence[str] | None = None,
        require_claims: Sequence[str] | None = None,
        verify_expiry: bool = True,
        verify_issued_at: bool = True,
        verify_jwt_id: bool = True,
        verify_not_before: bool = True,
        verify_subject: bool = True,
        strict_audience: bool = False,
        enforce_minimum_key_length: bool = True,
    ) -> None:
        """
        Apply possible customizations.

        On top of the regular jwt settings, *auth_header* selects
        the header to read, and *auth_scheme* is the prefix
        that the header value must start with.
        *www_authenticate* controls whether ``401`` responses advertise
        this auth in the ``WWW-Authenticate`` header.
        """
        super().__init__(
            user_id_field=user_id_field,
            algorithm=algorithm,
            security_scheme_name=security_scheme_name,
            secret=secret,
            token_cls=token_cls,
            leeway=leeway,
            accepted_audiences=accepted_audiences,
            accepted_issuers=accepted_issuers,
            require_claims=require_claims,
            verify_expiry=verify_expiry,
            verify_issued_at=verify_issued_at,
            verify_jwt_id=verify_jwt_id,
            verify_not_before=verify_not_before,
            verify_subject=verify_subject,
            strict_audience=strict_audience,
            enforce_minimum_key_length=enforce_minimum_key_length,
        )
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme
        self.www_authenticate = www_authenticate


#: Backwards compatible alias of :class:`HeaderJWTSyncAuth`.
JWTSyncAuth: TypeAlias = HeaderJWTSyncAuth

#: Backwards compatible alias of :class:`HeaderJWTAsyncAuth`.
JWTAsyncAuth: TypeAlias = HeaderJWTAsyncAuth
