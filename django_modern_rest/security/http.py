from abc import abstractmethod
from base64 import b64decode
from typing import TYPE_CHECKING, Any, ClassVar
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
    from django_modern_rest.serialization import BaseSerializer


class _HttpBasicAuth:
    __slots__ = ('_header',)

    security_scheme_name: ClassVar[str] = 'http_basic'

    def __init__(self, header: str = 'Authorization') -> None:
        self._header = header

    @property
    def security_scheme(self) -> Components:
        """"""
        return Components(
            security_schemes={
                self.security_scheme_name: SecurityScheme(
                    type='http',
                    name=self._header,
                    security_scheme_in='header',
                    scheme='basic',
                    description='Http Basic auth',
                ),
            },
        )

    @property
    def security_requirement(self) -> SecurityRequirement:
        """"""
        return {self.security_scheme_name: []}

    def _get_username_and_password(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> tuple[str, str] | None:
        header = controller.request.headers.get(self._header)
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
    __slots__ = ()

    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        login_data = self._get_username_and_password(controller)
        if login_data is None:
            return None
        return self.authenticate(endpoint, controller, *login_data)

    @abstractmethod
    def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        ussername: str,
        password: str,
    ) -> Any | None:
        """"""


class HttpBasicAsyncAuth(_HttpBasicAuth, AsyncAuth):
    __slots__ = ()

    @override
    async def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        login_data = self._get_username_and_password(controller)
        if login_data is None:
            return None
        return await self.authenticate(endpoint, controller, *login_data)

    @abstractmethod
    async def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        ussername: str,
        password: str,
    ) -> Any | None:
        """"""
