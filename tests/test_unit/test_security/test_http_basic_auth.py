import pytest
from inline_snapshot import snapshot

from dmr.openapi.objects import SecurityScheme
from dmr.security.http import HttpBasicAsyncAuth, HttpBasicSyncAuth


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
