import pytest
from inline_snapshot import snapshot

from dmr.openapi.objects import SecurityScheme
from dmr.security.http import (
    HttpBasicAsyncAuth,
    HttpBasicSyncAuth,
)


@pytest.mark.parametrize('typ', [HttpBasicSyncAuth, HttpBasicAsyncAuth])
def test_schema(
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
