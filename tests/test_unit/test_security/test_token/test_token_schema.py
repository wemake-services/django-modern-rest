import pytest
from inline_snapshot import snapshot

from dmr.openapi.objects import SecurityScheme
from dmr.security.token import (
    CookieTokenAsyncAuth,
    CookieTokenSyncAuth,
    QueryTokenAsyncAuth,
    QueryTokenSyncAuth,
    TokenAsyncAuth,
    TokenSyncAuth,
)


@pytest.mark.parametrize('typ', [TokenSyncAuth, TokenAsyncAuth])
def test_default_schema(
    *,
    typ: type[TokenSyncAuth] | type[TokenAsyncAuth],
) -> None:
    """Ensures that security scheme is correct for token auth."""
    instance = typ()

    assert instance.security_schemes == snapshot({
        'token': SecurityScheme(
            type='apiKey',
            name='X-API-Token',
            security_scheme_in='header',
            description='Opaque token authentication',
        ),
    })
    assert instance.security_requirement == snapshot({'token': []})


@pytest.mark.parametrize('typ', [TokenSyncAuth, TokenAsyncAuth])
def test_authorization_header_schema(
    *,
    typ: type[TokenSyncAuth] | type[TokenAsyncAuth],
) -> None:
    """Ensures Authorization header emits the OpenAPI `http` bearer scheme."""
    instance = typ(header_name='Authorization', security_scheme_name='token')

    assert instance.security_schemes == snapshot({
        'token': SecurityScheme(
            type='http',
            scheme='bearer',
            description='Opaque token authentication',
        ),
    })
    assert instance.security_requirement == snapshot({'token': []})


@pytest.mark.parametrize('typ', [TokenSyncAuth, TokenAsyncAuth])
def test_custom_header_schema(
    *,
    typ: type[TokenSyncAuth] | type[TokenAsyncAuth],
) -> None:
    """Ensures that a custom header is reflected in the schema."""
    instance = typ(header_name='X-Api-Token', security_scheme_name='apiToken')

    assert instance.security_schemes == snapshot({
        'apiToken': SecurityScheme(
            type='apiKey',
            name='X-Api-Token',
            security_scheme_in='header',
            description='Opaque token authentication',
        ),
    })
    assert instance.security_requirement == snapshot({'apiToken': []})


@pytest.mark.parametrize('typ', [QueryTokenSyncAuth, QueryTokenAsyncAuth])
def test_query_token_schema(
    *,
    typ: type[QueryTokenSyncAuth] | type[QueryTokenAsyncAuth],
) -> None:
    """Ensures QueryToken auth emits an apiKey query security scheme."""
    instance = typ()

    assert instance.security_schemes == snapshot({
        'token': SecurityScheme(
            type='apiKey',
            name='token',
            security_scheme_in='query',
            description='Opaque token authentication via query string',
        ),
    })
    assert instance.security_requirement == snapshot({'token': []})


@pytest.mark.parametrize('typ', [CookieTokenSyncAuth, CookieTokenAsyncAuth])
def test_cookie_token_schema(
    *,
    typ: type[CookieTokenSyncAuth] | type[CookieTokenAsyncAuth],
) -> None:
    """Ensures CookieToken auth emits an apiKey cookie security scheme."""
    instance = typ()

    assert instance.security_schemes == snapshot({
        'token': SecurityScheme(
            type='apiKey',
            name='token',
            security_scheme_in='cookie',
            description='Opaque token authentication via cookie',
        ),
    })
    assert instance.security_requirement == snapshot({'token': []})
