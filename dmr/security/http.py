from abc import abstractmethod
from base64 import b64decode, b64encode
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

from typing_extensions import override

from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.openapi.objects.security_requirement import (
    SecurityRequirement,
)
from django_modern_rest.openapi.objects.security_scheme import SecurityScheme
from django_modern_rest.security.base import AsyncAuth, SyncAuth

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.serializer import BaseSerializer


class _HttpBasicAuth:
    __slots__ = ('header', 'security_scheme_name')

    def __init__(
        self,
        *,
        security_scheme_name: str = 'http_basic',
        header: str = 'Authorization',
    ) -> None:
        """Apply possible customizations."""
        self.security_scheme_name = security_scheme_name
        self.header = header

    @property
    def security_scheme(self) -> Components:
        """Provides a security schema definition."""
        return Components(
            security_schemes={
                self.security_scheme_name: SecurityScheme(
                    type='http',
                    name=self.header,
                    security_scheme_in='header',
                    scheme='basic',
                    description='Http Basic auth',
                ),
            },
        )

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Provides a security schema usage requirement."""
        return {self.security_scheme_name: []}

    def _get_username_and_password(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> tuple[str, str] | None:
        header = controller.request.headers.get(self.header)
        if not header:
            return None

        parts = header.split(' ')
        if len(parts) == 1:
            encoded = parts[0]
        elif len(parts) == 2 and parts[0].lower() == 'basic':
            encoded = parts[1]
        else:
            return None

        try:
            username, password = b64decode(encoded).decode().split(':', 1)
        except Exception:
            return None
        return unquote(username), unquote(password)


class HttpBasicSyncAuth(_HttpBasicAuth, SyncAuth):
    """
    Uses HTTP Basic Auth.

    Subclass this type to provide actual username/password
    check according to your needs.
    This class is used for sync endpoints.

    .. warning::

        HTTP Basic Auth is not really secure and should
        not be used for anything serious.
        Consider using JWT instead.

    See also:
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication#basic_authentication_scheme

    """

    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
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
    ) -> Any | None:
        """Override this method to provide an actual user/password check."""
        raise NotImplementedError


class HttpBasicAsyncAuth(_HttpBasicAuth, AsyncAuth):
    """
    Uses HTTP Basic Auth.

    Subclass this type to provide actual username/password
    check according to your needs.
    This class is used for async endpoints.

    .. warning::

        HTTP Basic Auth is not really secure and should
        not be used for anything serious.
        Consider using JWT instead.

    See also:
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication#basic_authentication_scheme

    """

    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
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
    ) -> Any | None:
        """Override this method to provide an actual user/password check."""
        raise NotImplementedError


def basic_auth(username: str, password: str, *, prefix: str = 'Basic ') -> str:
    """
    Return a header value for basic auth for a given *username* and *password*.

    .. code:: python

      >>> basic_auth('admin', 'pass')
      'Basic YWRtaW46cGFzcw=='

      >>> basic_auth('admin', 'pass', prefix='')
      'YWRtaW46cGFzcw=='

    """
    token = b64encode(f'{username}:{password}'.encode()).decode('utf8')
    return f'{prefix}{token}'
