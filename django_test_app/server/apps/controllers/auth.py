from typing import TYPE_CHECKING, Any, final

from typing_extensions import override

from django_modern_rest.security.http import (
    HttpBasicAsyncAuth,
    HttpBasicSyncAuth,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.serialization import BaseSerializer


@final
class HttpBasicAsync(HttpBasicAsyncAuth):
    @override
    async def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        username: str,
        password: str,
    ) -> Any | None:
        if username == 'test' and password == 'pass':  # noqa: S105
            return True
        return None


@final
class HttpBasicSync(HttpBasicSyncAuth):
    @override
    def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        username: str,
        password: str,
    ) -> Any | None:
        if username == 'test' and password == 'pass':  # noqa: S105
            return True
        return None
