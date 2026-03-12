import pytest
from inline_snapshot import snapshot

from dmr.openapi.objects import SecurityScheme
from dmr.security.jwt import JWTAsyncAuth, JWTSyncAuth


@pytest.mark.parametrize('typ', [JWTSyncAuth, JWTAsyncAuth])
def test_schema(
    typ: type[JWTSyncAuth] | type[JWTAsyncAuth],
) -> None:
    """Ensures that security scheme is correct for jwt auth."""
    instance = typ()

    assert instance.security_scheme == snapshot({
        'jwt': SecurityScheme(
            type='http',
            description='JWT token auth',
            scheme='Bearer',
            bearer_format='JWT',
        ),
    })
    assert instance.security_requirement == snapshot({'jwt': []})
