from typing import Final

from django.http import HttpRequest
from typing_extensions import override

from dmr.openapi.objects import Reference, SecurityScheme
from dmr.security.token.auth.header import TokenAsyncAuth, TokenSyncAuth

_DEFAULT_PARAM: Final = 'token'


class QueryTokenSyncAuth(TokenSyncAuth):
    """
    Sync opaque token auth reading from a query string parameter.

    .. warning::
        Tokens in query strings appear in server access logs, browser history,
        and HTTP ``Referer`` headers.  Prefer :class:`TokenSyncAuth` for any
        context where security is a concern.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        query_param: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        update_last_used: bool = True,
    ) -> None:
        """Apply possible customizations."""
        super().__init__(
            query_param=query_param,
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
        )

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.query_param,
                security_scheme_in='query',
                description='Opaque token authentication via query string',
            ),
        }

    @override
    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Read the raw token from the query string."""
        return request.GET.get(self.query_param)


class QueryTokenAsyncAuth(TokenAsyncAuth):
    """
    Async opaque token auth reading from a query string parameter.

    .. warning::
        Tokens in query strings appear in server access logs, browser history,
        and HTTP ``Referer`` headers.  Prefer :class:`TokenAsyncAuth` for any
        context where security is a concern.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        query_param: str = _DEFAULT_PARAM,
        security_scheme_name: str = _DEFAULT_PARAM,
        update_last_used: bool = True,
    ) -> None:
        """Apply possible customizations."""
        super().__init__(
            query_param=query_param,
            security_scheme_name=security_scheme_name,
            update_last_used=update_last_used,
        )

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.query_param,
                security_scheme_in='query',
                description='Opaque token authentication via query string',
            ),
        }

    @override
    def get_raw_token(self, request: HttpRequest) -> str | None:
        """Read the raw token from the query string."""
        return request.GET.get(self.query_param)
