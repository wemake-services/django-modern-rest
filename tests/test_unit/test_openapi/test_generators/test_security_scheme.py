from typing import Final, Self

import pytest
from inline_snapshot import snapshot
from typing_extensions import override

from dmr.controller import Controller
from dmr.endpoint import Endpoint
from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.security_scheme import SecuritySchemeGenerator
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security import SyncAuth
from dmr.serializer import BaseSerializer

_TEST_CONFIG: Final = OpenAPIConfig(title='Test API', version='1.0.0')


class _NoSchemeAuth(SyncAuth):
    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        raise NotImplementedError

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        return {}

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return {'noScheme': []}


class _WithSchemeAuth(SyncAuth):
    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Self | None:
        raise NotImplementedError

    @property
    @override
    def security_schemes(self) -> dict[str, SecurityScheme | Reference]:
        return {
            'testScheme': SecurityScheme(type='http', scheme='bearer'),
        }

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return {'testScheme': []}


@pytest.fixture
def generator(openapi_context: OpenAPIContext) -> SecuritySchemeGenerator:
    """Create ``SecuritySchemeGenerator`` instance for testing."""
    return openapi_context.generators.security_scheme


def test_security_scheme_generator_no_schemes(
    generator: SecuritySchemeGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that auth providers without schemes are handled."""
    auth = _NoSchemeAuth()
    requirements = generator([auth], PydanticSerializer)

    assert requirements == [{'noScheme': []}]
    assert len(openapi_context.registries.security_scheme.schemes) == 0


def test_security_scheme_generator_with_schemes(
    generator: SecuritySchemeGenerator,
    openapi_context: OpenAPIContext,
) -> None:
    """Ensure that auth providers with schemes are handled."""
    auth = _WithSchemeAuth()
    requirements = generator([auth], PydanticSerializer)

    assert requirements == [{'testScheme': []}]
    assert openapi_context.registries.security_scheme.schemes == snapshot({
        'testScheme': SecurityScheme(type='http', scheme='bearer'),
    })
