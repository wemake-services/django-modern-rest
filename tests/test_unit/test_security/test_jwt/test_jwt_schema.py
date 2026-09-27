import pytest
from inline_snapshot import snapshot

from dmr import Controller
from dmr.openapi.objects import SecurityScheme
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.security.jwt import HeaderJWTAsyncAuth, HeaderJWTSyncAuth


class _Controller(Controller[PydanticFastSerializer]):
    def get(self) -> str:
        raise NotImplementedError


@pytest.mark.parametrize('typ', [HeaderJWTSyncAuth, HeaderJWTAsyncAuth])
def test_schema(
    *,
    typ: type[HeaderJWTSyncAuth] | type[HeaderJWTAsyncAuth],
) -> None:
    """Ensures that security scheme is correct for jwt auth."""
    metadata = _Controller.api_endpoints['GET'].metadata
    instance = typ()

    assert instance.security_schemes(metadata, _Controller) == snapshot({
        'jwt': SecurityScheme(
            type='http',
            description='JWT token auth',
            scheme='Bearer',
            bearer_format='JWT',
        ),
    })
    assert instance.security_requirements(metadata, _Controller) == snapshot([
        {'jwt': []},
    ])


@pytest.mark.parametrize('typ', [HeaderJWTSyncAuth, HeaderJWTAsyncAuth])
def test_custom_header_schema(
    *,
    typ: type[HeaderJWTSyncAuth] | type[HeaderJWTAsyncAuth],
) -> None:
    """Ensures that custom jwt auth is documented with the real header."""
    metadata = _Controller.api_endpoints['GET'].metadata
    instance = typ(auth_header='X-Api-Auth', auth_scheme='JWT')

    assert instance.security_schemes(metadata, _Controller) == snapshot({
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
    assert instance.security_requirements(metadata, _Controller) == snapshot([
        {'jwt': []},
    ])


@pytest.mark.parametrize('typ', [HeaderJWTSyncAuth, HeaderJWTAsyncAuth])
def test_custom_scheme_schema(
    *,
    typ: type[HeaderJWTSyncAuth] | type[HeaderJWTAsyncAuth],
) -> None:
    """Ensures that non-bearer JWT auth is documented as a header contract."""
    metadata = _Controller.api_endpoints['GET'].metadata
    instance = typ(auth_scheme='JWT')

    assert instance.security_schemes(metadata, _Controller) == snapshot({
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
    assert instance.security_requirements(metadata, _Controller) == snapshot([
        {'jwt': []},
    ])
