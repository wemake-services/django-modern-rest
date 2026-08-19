import pytest
from inline_snapshot import snapshot

from dmr.openapi.objects import SecurityScheme
from dmr.security.allauth import XSessionTokenAsyncAuth, XSessionTokenSyncAuth

_AuthType = type[XSessionTokenSyncAuth] | type[XSessionTokenAsyncAuth]


@pytest.mark.parametrize(
    'typ',
    [XSessionTokenSyncAuth, XSessionTokenAsyncAuth],
)
def test_schema(*, typ: _AuthType) -> None:
    """Ensures that security scheme is correct for allauth session tokens."""
    instance = typ()

    assert instance.security_schemes == snapshot({
        'session_token': SecurityScheme(
            type='apiKey',
            description='`django-allauth` headless session token',
            name='X-Session-Token',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirement == snapshot({'session_token': []})


@pytest.mark.parametrize(
    'typ',
    [XSessionTokenSyncAuth, XSessionTokenAsyncAuth],
)
def test_custom_schema(*, typ: _AuthType) -> None:
    """Ensures that header and scheme names are customizable."""
    instance = typ(
        header_name='Authorization',
        security_scheme_name='allauth',
    )

    assert instance.security_schemes == snapshot({
        'allauth': SecurityScheme(
            type='apiKey',
            description='`django-allauth` headless session token',
            name='Authorization',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirement == snapshot({'allauth': []})
