from typing import TYPE_CHECKING

from django.http import HttpRequest

from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme

if TYPE_CHECKING:
    from dmr.security.token.models import Token


class _BaseTokenAuth:  # pyright: ignore[reportUnusedClass]
    """Base class for DB-backed opaque token authentication.

    .. note::

        By default every successful authentication performs an extra
        ``UPDATE`` to persist ``last_used_at``.  Pass
        ``update_last_used=False`` to skip this write for high-traffic
        endpoints where tracking last-use is not required.
    """

    __slots__ = (
        'cookie_name',
        'header_name',
        'prefix',
        'query_param',
        'security_scheme_name',
        'update_last_used',
    )

    def __init__(
        self,
        *,
        header_name: str = 'X-API-Token',
        prefix: str = '',
        query_param: str = 'token',
        cookie_name: str = 'token',
        security_scheme_name: str = 'token',
        update_last_used: bool = True,
    ) -> None:
        """
        Apply possible customizations.

        - *header_name* — which header carries the raw token (default
          ``X-API-Token``).  Use ``'Authorization'`` for RFC 7235-style
          bearer auth (see *prefix* below).
        - *prefix* — scheme prefix expected before the token in the header
          value (default ``''``, i.e. the header value is used verbatim).
          Set to ``'Token'`` or ``'Bearer'`` when *header_name* is
          ``'Authorization'`` — e.g. ``prefix='Token'`` requires the client
          to send ``Authorization: Token <raw-token>``.
        - *query_param* — which query string parameter carries the raw token
          (default ``token``).
        - *cookie_name* — which cookie carries the raw token (default
          ``token``).
        - *security_scheme_name* — name used in OpenAPI security scheme map.

        **Common configurations:**

        .. code-block:: python

            # Default — custom header, no prefix
            >>> TokenSyncAuth()  # X-API-Token: <token>

            # DRF-compatible
            >>> TokenSyncAuth(header_name='Authorization', prefix='Token')

            # Bearer style
            >>> TokenSyncAuth(header_name='Authorization', prefix='Bearer')
        """
        self.header_name = header_name
        self.prefix = prefix
        self.query_param = query_param
        self.cookie_name = cookie_name
        self.security_scheme_name = security_scheme_name
        self.update_last_used = update_last_used

    def token_model(self) -> 'type[Token]':
        """Returns the Token model. Override to use a custom model."""
        from dmr.security.token.models import Token  # noqa: PLC0415

        return Token

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        if self.header_name == 'Authorization':
            # RFC 7235 reserves the Authorization header for the `http` scheme.
            # Using `apiKey` + `name: Authorization` is invalid in OpenAPI 3.x.
            return {
                self.security_scheme_name: SecurityScheme(
                    type='http',
                    scheme='bearer',
                    description='Opaque token authentication',
                ),
            }
        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.header_name,
                security_scheme_in='header',
                description='Opaque token authentication',
            ),
        }

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}

    def get_raw_token(self, request: HttpRequest) -> str | None:
        """
        Extract the raw token string from the request.

        By default reads from the header specified by *header_name*, stripping
        any *prefix*.  Override this method to read from a different source
        (cookie, query string, request body, etc.).
        """
        header_value = request.headers.get(self.header_name)
        if header_value is None:
            return None
        if self.prefix:
            expected = f'{self.prefix} '
            if not header_value.startswith(expected):
                return None
            return header_value[len(expected) :]
        return header_value
