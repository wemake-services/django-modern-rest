import pytest

from dmr.openapi.core.registry import SecuritySchemeRegistry
from dmr.openapi.objects import Reference, SecurityScheme


def _http_bearer() -> SecurityScheme:
    return SecurityScheme(type='http', scheme='bearer', bearer_format='JWT')


def _api_key_header() -> SecurityScheme:
    return SecurityScheme(
        type='apiKey',
        name='X-API-Key',
        security_scheme_in='header',
    )


def test_register_unique_security_schemes() -> None:
    """Test that registering unique security scheme names succeeds."""
    registry = SecuritySchemeRegistry()
    bearer = _http_bearer()
    api_key = _api_key_header()

    registry.register('BearerAuth', bearer)
    registry.register('ApiKeyAuth', api_key)

    assert registry.schemes == {
        'BearerAuth': bearer,
        'ApiKeyAuth': api_key,
    }


def test_reregister_identical_security_scheme_is_allowed() -> None:
    """Same name with an equal scheme is idempotent (shared auth)."""
    registry = SecuritySchemeRegistry()
    first = _http_bearer()
    second = _http_bearer()

    registry.register('BearerAuth', first)
    registry.register('BearerAuth', second)

    assert registry.schemes == {'BearerAuth': first}


def test_duplicate_security_scheme_name_raises_error() -> None:
    """Different schemes under one name must raise ``ValueError``."""
    registry = SecuritySchemeRegistry()
    registry.register('Auth', _http_bearer())

    with pytest.raises(
        ValueError,
        match="Security scheme 'Auth' is already registered",
    ):
        registry.register('Auth', _api_key_header())


def test_duplicate_reference_name_raises_error() -> None:
    """Different references under one name must raise ``ValueError``."""
    registry = SecuritySchemeRegistry()
    registry.register('Auth', Reference(ref='#/components/securitySchemes/A'))

    with pytest.raises(
        ValueError,
        match="Security scheme 'Auth' is already registered",
    ):
        registry.register(
            'Auth',
            Reference(ref='#/components/securitySchemes/B'),
        )
