import pytest

from dmr.openapi.core.registry import SecuritySchemeRegistry
from dmr.openapi.objects import SecurityScheme


def test_multiple_unique_security_schemes() -> None:
    """Test that registering multiple unique security schemes succeeds."""
    registry = SecuritySchemeRegistry()
    schemes = {
        'BearerAuth': SecurityScheme(type='http', scheme='bearer'),
        'ApiKeyAuth': SecurityScheme(
            type='apiKey',
            name='X-API-Key',
            security_scheme_in='header',
        ),
    }

    for name, scheme in schemes.items():
        registry.register(name, scheme)

    assert registry.schemes == schemes


def test_duplicate_security_scheme_raises_error() -> None:
    """Test that registering a duplicate security scheme raises ``ValueError``."""
    registry = SecuritySchemeRegistry()
    scheme = SecurityScheme(type='http', scheme='bearer')
    registry.register('BearerAuth', scheme)

    with pytest.raises(
        ValueError,
        match="Security scheme 'BearerAuth' is already registered",
    ):
        registry.register('BearerAuth', scheme)
