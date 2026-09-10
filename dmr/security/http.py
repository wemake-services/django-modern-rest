from abc import abstractmethod
from base64 import b64decode, b64encode
from typing import TYPE_CHECKING, Final, Self

from typing_extensions import override

from dmr.exceptions import NotAuthenticatedError
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security.base import AsyncAuth, SyncAuth

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

# Default protection space that we advertise in `WWW-Authenticate`:
_DEFAULT_BASIC_REALM: Final = 'api'


class _HttpBasicAuth:  # noqa: WPS214
    """
    Shared parts of the sync and async http basic auth.

    .. versionchanged:: 0.15.0

        Added the ``auth_scheme`` prefix, which is required by default.
        See :class:`HttpBasicSyncAuth` and :class:`HttpBasicAsyncAuth`.

    """

    __slots__ = (
        'auth_scheme',
        'header',
        'realm',
        'security_scheme_name',
        'www_authenticate',
    )

    def __init__(  # noqa: WPS211
        self,
        *,
        security_scheme_name: str = 'http_basic',
        header: str = 'Authorization',
        auth_scheme: str = 'Basic',
        www_authenticate: bool = True,
        realm: str = _DEFAULT_BASIC_REALM,
    ) -> None:
        """
        Apply possible customizations.

        - *security_scheme_name* is the name
          used in the OpenAPI security scheme map
        - *header* selects the header to read the credentials from
        - *auth_scheme* is the prefix that the header value must start with,
          it is matched exactly, so ``Basic`` won't accept ``basic``.
          Pass an empty string to read the credentials without any prefix
        - *www_authenticate* controls whether ``401`` responses
          advertise this auth in the ``WWW-Authenticate`` header.
          Turn it off to stop browsers from showing
          their native login prompt for this API.
        - *realm* names the protection space in that challenge.
          :rfc:`7617#section-2` requires it for the ``Basic`` scheme.

        """
        self.security_scheme_name = security_scheme_name
        self.header = header
        self.auth_scheme = auth_scheme
        self.www_authenticate = www_authenticate
        self.realm = realm

    @property
    def www_authenticate_challenge(self) -> str | None:
        """
        Challenge for the ``Basic`` scheme.

        Returns ``None`` for a custom *header* or *auth_scheme*,
        because a challenge can only ask the client
        for the ``Basic`` prefix in the ``Authorization`` header.
        """
        if (
            not self.www_authenticate
            or not self._uses_standard_http_basic_auth()
        ):
            return None
        # `charset` is defined by RFC 7617 and tells the client to encode
        # credentials as UTF-8, which is what we decode them as
        # in `_get_username_and_password`.
        return f'Basic realm={_quote_auth_param(self.realm)}, charset="UTF-8"'

    @property
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        if self._uses_standard_http_basic_auth():
            return {
                self.security_scheme_name: SecurityScheme(
                    type='http',
                    scheme='basic',
                    description='Http Basic auth',
                ),
            }

        return {
            self.security_scheme_name: SecurityScheme(
                type='apiKey',
                name=self.header,
                security_scheme_in='header',
                description=self._get_custom_security_scheme_description(),
            ),
        }

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}

    def _get_username_and_password(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> tuple[str, str] | None:
        # We return `None` here, because it might be some other auth.
        # We don't want to falsely trigger any errors just yet.
        header = controller.request.headers.get(self.header)
        if not header:
            return None
        encoded = self._split_encoded_credentials(header)
        if encoded is None:
            return None

        # After this point we are sure that these are basic auth credentials.
        # So, broken ones are an error and not a reason to try other authes.
        try:
            username, password = b64decode(encoded).decode().split(':', 1)
        except Exception:
            raise NotAuthenticatedError from None
        return username, password

    def _split_encoded_credentials(self, header: str) -> str | None:
        """Splits string like 'Basic credentials' and returns 'credentials'."""
        if not self.auth_scheme:  # Empty scheme means "no prefix at all".
            return header

        parts = header.split(' ')
        if len(parts) != 2 or parts[0] != self.auth_scheme:
            # This header does not belong to us: it can be a header
            # of any other auth from the chain. Raising here would fail
            # the whole request and would not let the others even try.
            # So, we return `None` and the next auth gets its chance.
            return None
        return parts[1]

    def _uses_standard_http_basic_auth(self) -> bool:
        """Whether the auth contract matches OpenAPI HTTP basic auth."""
        return self.header == 'Authorization' and self.auth_scheme == 'Basic'

    def _get_custom_security_scheme_description(self) -> str:
        """Describe non-standard basic auth header contracts."""
        # Empty `auth_scheme` means that the header carries
        # the credentials alone, without a prefix and a space after it.
        scheme_prefix = f'{self.auth_scheme} ' if self.auth_scheme else ''
        return (
            'HTTP Basic auth via '
            f'`{self.header}` header using '
            f'`{scheme_prefix}<base64(username:password)>` format'
        )


class HttpBasicSyncAuth(_HttpBasicAuth, SyncAuth):
    """
    Uses HTTP Basic Auth.

    Subclass this type to provide actual username/password
    check according to your needs.
    This class is used for sync endpoints.

    Note that this class does not set ``request.user`` by design.
    Because many users might use the same auth parameters.

    .. warning::

        HTTP Basic Auth is not really secure and should
        not be used for anything serious.
        Consider using JWT instead.

    See also:
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication#basic_authentication_scheme

    .. versionchanged:: 0.15.0

        The ``auth_scheme`` prefix is now required and configurable,
        it is ``Basic`` by default. Header values without a prefix
        are only accepted with ``auth_scheme=''``.

    """

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Does the login routine."""
        login_data = self._get_username_and_password(controller)
        if login_data is None:
            return None
        return self.authenticate(endpoint, controller, *login_data)

    @abstractmethod
    def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        username: str,
        password: str,
    ) -> Self | None:
        """Override this method to provide an actual user/password check."""
        raise NotImplementedError


class HttpBasicAsyncAuth(_HttpBasicAuth, AsyncAuth):
    """
    Uses HTTP Basic Auth.

    Subclass this type to provide actual username/password
    check according to your needs.
    This class is used for async endpoints.

    Note that this class does not set ``request.user`` by design.
    Because many users might use the same auth parameters.

    .. warning::

        HTTP Basic Auth is not really secure and should
        not be used for anything serious.
        Consider using JWT instead.

    See also:
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication#basic_authentication_scheme

    .. versionchanged:: 0.15.0

        The ``auth_scheme`` prefix is now required and configurable,
        it is ``Basic`` by default. Header values without a prefix
        are only accepted with ``auth_scheme=''``.

    """

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        """Does the login routine."""
        login_data = self._get_username_and_password(controller)
        if login_data is None:
            return None
        return await self.authenticate(endpoint, controller, *login_data)

    @abstractmethod
    async def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        username: str,
        password: str,
    ) -> Self | None:
        """Override this method to provide an actual user/password check."""
        raise NotImplementedError


def basic_auth(username: str, password: str, *, prefix: str = 'Basic ') -> str:
    """
    Return a header value for basic auth for a given *username* and *password*.

    The *prefix* must match the ``auth_scheme`` of the auth class
    that will read this header, including the trailing space.

    .. code:: python

      >>> basic_auth('admin', 'pass')
      'Basic YWRtaW46cGFzcw=='

      >>> basic_auth('admin', 'pass', prefix='Custom ')
      'Custom YWRtaW46cGFzcw=='

    """
    token = b64encode(f'{username}:{password}'.encode()).decode('utf8')
    return f'{prefix}{token}'


def _quote_auth_param(auth_param: str) -> str:
    r"""
    Return *value* as a ``quoted-string`` auth param, as :rfc:`9110` wants it.

    .. code:: python

      >>> _quote_auth_param('api')
      '"api"'

      >>> _quote_auth_param('say "hi"')
      '"say \\"hi\\""'

    """
    escaped = auth_param.replace('\\', r'\\').replace('"', r'\"')
    return f'"{escaped}"'
