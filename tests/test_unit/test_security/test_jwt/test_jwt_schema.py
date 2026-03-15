import pytest
from inline_snapshot import snapshot

from dmr.openapi.objects import SecurityScheme
from dmr.security.jwt import JWTAsyncAuth, JWTSyncAuth


@pytest.mark.parametrize('typ', [JWTSyncAuth, JWTAsyncAuth])
def test_schema(
    *,
    typ: type[JWTSyncAuth] | type[JWTAsyncAuth],
) -> None:
    """Ensures that security scheme is correct for jwt auth."""
    instance = typ()

    assert instance.security_schemes == snapshot({
        'jwt': SecurityScheme(
            type='http',
            description='JWT token auth',
            scheme='Bearer',
            bearer_format='JWT',
        ),
    })
    assert instance.security_requirement == snapshot({'jwt': []})


@pytest.mark.parametrize('typ', [JWTSyncAuth, JWTAsyncAuth])
def test_custom_header_schema(
    *,
    typ: type[JWTSyncAuth] | type[JWTAsyncAuth],
) -> None:
    """Ensures that custom jwt auth is documented with the real header."""
    instance = typ(auth_header='X-Api-Auth', auth_scheme='JWT')

    assert instance.security_schemes == snapshot({
        'jwt': SecurityScheme(
            type='apiKey',
            description=(
                'JWT token auth via `X-Api-Auth` header '
                'using `JWT <token>` format'
            ),
            name='X-Api-Auth',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirement == snapshot({'jwt': []})


@pytest.mark.parametrize('typ', [JWTSyncAuth, JWTAsyncAuth])
def test_custom_scheme_schema(
    *,
    typ: type[JWTSyncAuth] | type[JWTAsyncAuth],
) -> None:
    """Ensures that non-bearer JWT auth is documented as a header contract."""
    instance = typ(auth_scheme='JWT')

    assert instance.security_schemes == snapshot({
        'jwt': SecurityScheme(
            type='apiKey',
            description=(
                'JWT token auth via `Authorization` header '
                'using `JWT <token>` format'
            ),
            name='Authorization',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirement == snapshot({'jwt': []})
