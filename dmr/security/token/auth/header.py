from typing import Final

from django.http import HttpRequest

from dmr.openapi.objects import Reference, SecurityScheme
from dmr.security.token.auth.base import (
    BaseTokenAsyncAuth,
    BaseTokenSyncAuth,
)
from dmr.security.token.token import DEFAULT_TOKEN_ALGORITHM, DEFAULT_TOKEN_SALT

_AUTH_DESCRIPTION: Final = 'Opaque token authentication'


class _BaseHeaderTokenAuth:
    __slots__ = ()

    header_name: str
    prefix: str
    security_scheme_name: str

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        if self.header_name == 'Authorization':
            return {
                self.security_scheme_name: SecurityScheme(
                    type='http',
                    scheme='bearer',
                    description=_AUTH_DESCRIPTION,
                ),
            }
        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.header_name,
                security_scheme_in='header',
                description=_AUTH_DESCRIPTION,
            ),
        }

    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Read the raw token from the request header, stripping any prefix."""
        header_value = request.headers.get(self.header_name)
        if header_value is None:
            return None
        if self.prefix:
            expected = f'{self.prefix} '
            if not header_value.startswith(expected):
                return None
            return header_value[len(expected) :]
        return header_value


class HeaderTokenSyncAuth(_BaseHeaderTokenAuth, BaseTokenSyncAuth):
    """Sync opaque token auth; reads from ``X-API-Token`` by default."""

    __slots__ = ('header_name', 'prefix')

    def __init__(
        self,
        *,
        header_name: str = 'X-API-Token',
        prefix: str = '',
        security_scheme_name: str = 'token',
        update_last_used: bool = False,
        token_secret: str | None = None,
        token_salt: str = DEFAULT_TOKEN_SALT,
        token_algorithm: str = DEFAULT_TOKEN_ALGORITHM,
    ) -> None:
        """
        Apply possible customizations.

        - *header_name* - which header carries the raw token (default
          ``X-API-Token``).  Use ``'Authorization'`` for RFC 7235-style
          bearer auth (see *prefix* below).
        - *prefix* - scheme prefix expected before the token in the header
          value (default ``''``, i.e. the header value is used verbatim).
          Set to ``'Token'`` or ``'Bearer'`` when *header_name* is
          ``'Authorization'`` - e.g. ``prefix='Token'`` requires the client
          to send ``Authorization: Token <raw-token>``.
        - *security_scheme_name* - name used in OpenAPI security scheme map.

        **Common configurations:**

        .. code-block:: python

            >>> from dmr.security.token.auth.header import HeaderTokenSyncAuth

            # Default - custom header, no prefix
            >>> auth = HeaderTokenSyncAuth()  # X-API-Token: <token>

            # DRF-compatible
            >>> auth = HeaderTokenSyncAuth(
            ...     header_name='Authorization',
            ...     prefix='Token',
            ... )

            # Bearer style
            >>> auth = HeaderTokenSyncAuth(
            ...     header_name='Authorization',
            ...     prefix='Bearer',
            ... )
        """
        super().__init__(
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
            token_secret=token_secret,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        )
        self.header_name = header_name
        self.prefix = prefix


class HeaderTokenAsyncAuth(_BaseHeaderTokenAuth, BaseTokenAsyncAuth):
    """Async opaque token auth; reads from ``X-API-Token`` by default."""

    __slots__ = ('header_name', 'prefix')

    def __init__(
        self,
        *,
        header_name: str = 'X-API-Token',
        prefix: str = '',
        security_scheme_name: str = 'token',
        update_last_used: bool = False,
        token_secret: str | None = None,
        token_salt: str = DEFAULT_TOKEN_SALT,
        token_algorithm: str = DEFAULT_TOKEN_ALGORITHM,
    ) -> None:
        """Apply possible customizations. See :class:`HeaderTokenSyncAuth`."""
        super().__init__(
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
            token_secret=token_secret,
            token_salt=token_salt,
            token_algorithm=token_algorithm,
        )
        self.header_name = header_name
        self.prefix = prefix
