import json
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


class _SyncAuth(HttpBasicSyncAuth):
    @override
    def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        if username == 'test' and password == 'pass':  # noqa: S105
            return self
        return None


class _AsyncAuth(HttpBasicAsyncAuth):
    @override
    async def authenticate(
        self,
        endpoint: Endpoint,
        controller: Controller[BaseSerializer],
        username: str,
        password: str,
    ) -> Self | None:
        if username == 'test' and password == 'pass':  # noqa: S105
            return self
        return None


class _SyncController(Controller[PydanticSerializer]):
    auth = (_SyncAuth(),)

    def get(self) -> str:
        return 'authed'


class _AsyncController(Controller[PydanticSerializer]):
    auth = (_AsyncAuth(),)

    async def get(self) -> str:
        return 'authed'


class _CustomSchemeSyncController(Controller[PydanticSerializer]):
    auth = (_SyncAuth(auth_scheme='Custom'),)

    def get(self) -> str:
        return 'authed'


class _CustomSchemeAsyncController(Controller[PydanticSerializer]):
    auth = (_AsyncAuth(auth_scheme='Custom'),)

    async def get(self) -> str:
        return 'authed'


#: Header and value that the fallback auth of chained controllers accepts.
_FALLBACK_HEADER: Final = 'X-Fallback-Auth'
_FALLBACK_VALUE: Final = basic_auth('test', 'pass')


class _ChainedSyncController(Controller[PydanticSerializer]):
    auth = (
        _SyncAuth(),
        _SyncAuth(header=_FALLBACK_HEADER, security_scheme_name='fallback'),
    )

    def get(self) -> str:
        return 'authed'


class _ChainedAsyncController(Controller[PydanticSerializer]):
    auth = (
        _AsyncAuth(),
        _AsyncAuth(header=_FALLBACK_HEADER, security_scheme_name='fallback'),
    )

    async def get(self) -> str:
        return 'authed'


#: Values that have the right prefix, but cannot be parsed at all.
_BROKEN_CREDENTIALS: Final = (
    'Basic not-a-base64',
    'Basic dGVzdEBwYXNz',  # `test@pass` encoded, missing the `:` separator
)

#: Values that must not be treated as basic auth credentials.
_UNSUPPORTED_SCHEMES: Final = (
    # Credentials without the `auth_scheme` prefix:
    basic_auth('test', 'pass', prefix=''),
    # `auth_scheme` is matched exactly, so casing matters:
    basic_auth('test', 'pass', prefix='basic '),
    # Some other auth might handle these:
    basic_auth('test', 'pass', prefix='Bearer '),
    # Prefix alone and extra parts are not valid either:
    'Basic',
    f'{basic_auth("test", "pass")} extra',
)


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
@pytest.mark.parametrize('auth_scheme', ['Basic', 'basic', 'BASIC'])
def test_standard_auth_scheme_schema(
    *,
    typ: type[HttpBasicSyncAuth] | type[HttpBasicAsyncAuth],
    auth_scheme: str,
) -> None:
    """Ensures that any casing of `Basic` is a standard http basic auth."""
    instance = typ(auth_scheme=auth_scheme)

    assert instance.security_schemes == snapshot({
        'http_basic': SecurityScheme(
            type='http',
            description='Http Basic auth',
            scheme='basic',
        ),
    })


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
                '`Basic <base64(username:password)>` format'
            ),
            name='X-Api-Auth',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirement == snapshot({'http_basic': []})


_USERNAME: Final = 'user%40name'
_PASSWORD: Final = 'pass%3Aword'  # noqa: S105

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


@pytest.mark.parametrize('typ', [HttpBasicSyncAuth, HttpBasicAsyncAuth])
def test_custom_auth_scheme_schema(
    typ: type[HttpBasicSyncAuth] | type[HttpBasicAsyncAuth],
) -> None:
    """Ensures that custom basic auth is documented with the real scheme."""
    instance = typ(auth_scheme='Custom')

    assert instance.security_schemes == snapshot({
        'http_basic': SecurityScheme(
            type='apiKey',
            description=(
                'HTTP Basic auth via `Authorization` header using '
                '`Custom <base64(username:password)>` format'
            ),
            name='Authorization',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirement == snapshot({'http_basic': []})


@pytest.mark.parametrize(
    ('auth_header', 'status_code'),
    [
        (basic_auth('test', 'pass'), HTTPStatus.OK),
        *[
            (auth_header, HTTPStatus.UNAUTHORIZED)
            for auth_header in _UNSUPPORTED_SCHEMES
        ],
    ],
)
def test_sync_auth_scheme(
    dmr_rf: DMRRequestFactory,
    *,
    auth_header: str,
    status_code: HTTPStatus,
) -> None:
    """Ensures that sync auth requires the exact `Basic` prefix."""
    request = dmr_rf.get('/whatever/', headers={'Authorization': auth_header})

    response = _SyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('auth_header', 'status_code'),
    [
        (basic_auth('test', 'pass'), HTTPStatus.OK),
        *[
            (auth_header, HTTPStatus.UNAUTHORIZED)
            for auth_header in _UNSUPPORTED_SCHEMES
        ],
    ],
)
async def test_async_auth_scheme(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    auth_header: str,
    status_code: HTTPStatus,
) -> None:
    """Ensures that async auth requires the exact `Basic` prefix."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'Authorization': auth_header},
    )

    response = await dmr_async_rf.wrap(_AsyncController.as_view()(request))

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content


@pytest.mark.parametrize(
    ('auth_header', 'status_code'),
    [
        (basic_auth('test', 'pass', prefix='Custom '), HTTPStatus.OK),
        (basic_auth('test', 'pass'), HTTPStatus.UNAUTHORIZED),
    ],
)
def test_sync_custom_auth_scheme(
    dmr_rf: DMRRequestFactory,
    *,
    auth_header: str,
    status_code: HTTPStatus,
) -> None:
    """Ensures that sync auth can require a custom prefix."""
    request = dmr_rf.get('/whatever/', headers={'Authorization': auth_header})

    response = _CustomSchemeSyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('auth_header', 'status_code'),
    [
        (basic_auth('test', 'pass', prefix='Custom '), HTTPStatus.OK),
        (basic_auth('test', 'pass'), HTTPStatus.UNAUTHORIZED),
    ],
)
async def test_async_custom_auth_scheme(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    auth_header: str,
    status_code: HTTPStatus,
) -> None:
    """Ensures that async auth can require a custom prefix."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={'Authorization': auth_header},
    )

    response = await dmr_async_rf.wrap(
        _CustomSchemeAsyncController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code, response.content


def test_sync_missing_header_is_skipped(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that a missing header lets the next sync auth run."""
    request = dmr_rf.get(
        '/whatever/',
        headers={_FALLBACK_HEADER: _FALLBACK_VALUE},
    )

    response = _ChainedSyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.asyncio
async def test_async_missing_header_is_skipped(
    dmr_async_rf: DMRAsyncRequestFactory,
) -> None:
    """Ensures that a missing header lets the next async auth run."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={_FALLBACK_HEADER: _FALLBACK_VALUE},
    )

    response = await dmr_async_rf.wrap(
        _ChainedAsyncController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert json.loads(response.content) == 'authed'


@pytest.mark.parametrize('auth_header', _BROKEN_CREDENTIALS)
def test_sync_broken_credentials_raise(
    dmr_rf: DMRRequestFactory,
    *,
    auth_header: str,
) -> None:
    """Ensures that broken credentials don't fall back to the next sync auth."""
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Authorization': auth_header,
            _FALLBACK_HEADER: _FALLBACK_VALUE,
        },
    )

    response = _ChainedSyncController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })


@pytest.mark.asyncio
@pytest.mark.parametrize('auth_header', _BROKEN_CREDENTIALS)
async def test_async_broken_credentials_raise(
    dmr_async_rf: DMRAsyncRequestFactory,
    *,
    auth_header: str,
) -> None:
    """Ensures that broken credentials don't fall back to the next auth."""
    request = dmr_async_rf.get(
        '/whatever/',
        headers={
            'Authorization': auth_header,
            _FALLBACK_HEADER: _FALLBACK_VALUE,
        },
    )

    response = await dmr_async_rf.wrap(
        _ChainedAsyncController.as_view()(request),
    )

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNAUTHORIZED, response.content
    assert json.loads(response.content) == snapshot({
        'detail': [{'msg': 'Not authenticated', 'type': 'security'}],
    })
