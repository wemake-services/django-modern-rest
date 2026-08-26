import pytest

from dmr.openapi.objects import SecurityScheme
from dmr.security.token import (
    CookieTokenAsyncAuth,
    CookieTokenSyncAuth,
    HeaderTokenAsyncAuth,
    HeaderTokenSyncAuth,
)


@pytest.mark.parametrize('typ', [HeaderTokenSyncAuth, HeaderTokenAsyncAuth])
@pytest.mark.parametrize('header_name', ['X-API-Token', 'custom'])
@pytest.mark.parametrize('security_scheme_name', ['token', 'customName'])
@pytest.mark.parametrize('prefix', ['', 'Bearer '])
def test_custom_header_schema(
    *,
    typ: type[HeaderTokenSyncAuth] | type[HeaderTokenAsyncAuth],
    header_name: str,
    security_scheme_name: str,
    prefix: str,
) -> None:
    """Ensures that a custom header is reflected in the schema."""
    instance = typ(
        header_name=header_name,
        security_scheme_name=security_scheme_name,
        prefix=prefix,  # it does not matter
    )

    assert instance.security_schemes == {
        security_scheme_name: SecurityScheme(
            type='apiKey',
            name=header_name,
            security_scheme_in='header',
            description='Opaque token authentication',
        ),
    }
    assert instance.security_requirement == {security_scheme_name: []}


@pytest.mark.parametrize('typ', [HeaderTokenSyncAuth, HeaderTokenAsyncAuth])
@pytest.mark.parametrize('security_scheme_name', ['token', 'customName'])
@pytest.mark.parametrize('prefix', ['', 'Bearer '])
def test_header_schema_for_authorization(
    *,
    typ: type[HeaderTokenSyncAuth] | type[HeaderTokenAsyncAuth],
    security_scheme_name: str,
    prefix: str,
) -> None:
    """Ensures that a custom header is reflected in the schema."""
    instance = typ(
        header_name='Authorization',
        security_scheme_name=security_scheme_name,
        prefix=prefix,  # it does not matter
    )

    assert instance.security_schemes == {
        security_scheme_name: SecurityScheme(
            type='http',
            scheme='bearer',
            description='Opaque token authentication',
        ),
    }
    assert instance.security_requirement == {security_scheme_name: []}


@pytest.mark.parametrize('typ', [CookieTokenSyncAuth, CookieTokenAsyncAuth])
@pytest.mark.parametrize('cookie_name', ['token', 'custom'])
@pytest.mark.parametrize('security_scheme_name', ['token', 'customName'])
def test_cookie_token_schema(
    *,
    typ: type[CookieTokenSyncAuth] | type[CookieTokenAsyncAuth],
    cookie_name: str,
    security_scheme_name: str,
) -> None:
    """Ensures CookieToken auth emits an apiKey cookie security scheme."""
    instance = typ(
        cookie_name=cookie_name,
        security_scheme_name=security_scheme_name,
    )

    assert instance.security_schemes == {
        security_scheme_name: SecurityScheme(
            type='apiKey',
            name=cookie_name,
            security_scheme_in='cookie',
            description='Opaque token authentication via cookie',
        ),
    }
    assert instance.security_requirement == {security_scheme_name: []}
