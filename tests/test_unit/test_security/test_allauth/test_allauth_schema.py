from typing import TypeAlias

import pytest
from inline_snapshot import snapshot

from dmr import Controller
from dmr.openapi.objects import SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.allauth import XSessionTokenAsyncAuth, XSessionTokenSyncAuth

_AuthType: TypeAlias = (
    type[XSessionTokenSyncAuth] | type[XSessionTokenAsyncAuth]
)


class _Controller(Controller[PydanticSerializer]):
    def get(self) -> str:
        raise NotImplementedError


@pytest.mark.parametrize(
    'typ',
    [XSessionTokenSyncAuth, XSessionTokenAsyncAuth],
)
def test_schema(*, typ: _AuthType) -> None:
    """Ensures that security scheme is correct for allauth session tokens."""
    metadata = _Controller.api_endpoints['GET'].metadata
    instance = typ()

    assert instance.security_schemes(metadata, _Controller) == snapshot({
        'session_token': SecurityScheme(
            type='apiKey',
            description='`django-allauth` headless session token',
            name='X-Session-Token',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirements(metadata, _Controller) == snapshot([
        {'session_token': []},
    ])


@pytest.mark.parametrize(
    'typ',
    [XSessionTokenSyncAuth, XSessionTokenAsyncAuth],
)
def test_custom_schema(*, typ: _AuthType) -> None:
    """Ensures that header and scheme names are customizable."""
    metadata = _Controller.api_endpoints['GET'].metadata
    instance = typ(
        header_name='Authorization',
        security_scheme_name='allauth',
    )

    assert instance.security_schemes(metadata, _Controller) == snapshot({
        'allauth': SecurityScheme(
            type='apiKey',
            description='`django-allauth` headless session token',
            name='Authorization',
            security_scheme_in='header',
        ),
    })
    assert instance.security_requirements(metadata, _Controller) == snapshot([
        {'allauth': []},
    ])
