from http import HTTPStatus
from typing import Final, Self, final

import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.openapi.objects import SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.http import HttpBasicAsyncAuth, HttpBasicSyncAuth, basic_auth
from dmr.serializer import BaseSerializer
from dmr.test import DMRAsyncRequestFactory, DMRRequestFactory


@pytest.mark.parametrize('typ', [HttpBasicSyncAuth, HttpBasicAsyncAuth])
def test_schema(
    *,
    typ: type[HttpBasicSyncAuth] | type[HttpBasicAsyncAuth],
) -> None:
    """Ensures that security scheme is correct for http basic auth."""
    instance = typ()

    assert instance.security_schemes == snapshot({
        'http_basic': SecurityScheme(
            type='http',
            description='Http Basic auth',
            scheme='basic',
        ),
    })
    assert instance.security_requirement == snapshot({'http_basic': []})


@pytest.mark.parametrize('typ', [HttpBasicSyncAuth, HttpBasicAsyncAuth])
def test_custom_header_schema(
    typ: type[HttpBasicSyncAuth] | type[HttpBasicAsyncAuth],
) -> None:
    """Ensures that custom basic auth is documented with the real header."""
    instance = typ(header='X-Api-Auth')

    assert instance.security_schemes == snapshot({
        'http_basic': SecurityScheme(
            type='apiKey',
            description=(
                'HTTP Basic auth via `X-Api-Auth` header using '
                '`<base64(username:password)>` or '
                '`Basic <base64(username:password)>` format'
            ),
            name='X-Api-Auth',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirement == snapshot({'http_basic': []})


_USERNAME: Final = 'user%40name'
_PASSWORD: Final = 'pass%3Aword'

_CREDENTIALS: Final = (
    ((_USERNAME, _PASSWORD), HTTPStatus.OK),
    (('user@name', _PASSWORD), HTTPStatus.UNAUTHORIZED),
    ((_USERNAME, 'pass:word'), HTTPStatus.UNAUTHORIZED),
    (('user@name', 'pass:word'), HTTPStatus.UNAUTHORIZED),
)


class _SyncPercentAuth(HttpBasicSyncAuth):
    __slots__ = ()

    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        if (username, password) == (_USERNAME, _PASSWORD):
            return self
        return None


class _AsyncPercentAuth(HttpBasicAsyncAuth):
    __slots__ = ()

    @override
    async def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        if (username, password) == (_USERNAME, _PASSWORD):
            return self
        return None


@final
class _SyncPercentController(Controller[PydanticSerializer]):
    auth = (_SyncPercentAuth(),)

    def get(self) -> str:
        return 'authed'


@final
class _AsyncPercentController(Controller[PydanticSerializer]):
    auth = (_AsyncPercentAuth(),)

    async def get(self) -> str:
        return 'authed'


@pytest.mark.parametrize(('credentials', 'status'), _CREDENTIALS)
def test_sync_percent_credentials(
    dmr_rf: DMRRequestFactory,
    *,
    credentials: tuple[str, str],
    status: HTTPStatus,
) -> None:
    """Ensures that sync auth never url-decodes the given credentials."""
    request = dmr_rf.get(
        '/whatever/',
        headers={'Authorization': basic_auth(*credentials)},
    )

    response = _SyncPercentController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status, response.content


@pytest.mark.asyncio
@pytest.mark.parametrize(('credentials', 'status'), _CREDENTIALS)
async def test_async_percent_credentials(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    credentials: tuple[str, str],
    status: HTTPStatus,
) -> None:
    """Ensures that async auth never url-decodes the given credentials."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'Authorization': basic_auth(*credentials)},
    )

    response = await dmr_async_rf.wrap(
        _AsyncPercentController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == status, response.content
