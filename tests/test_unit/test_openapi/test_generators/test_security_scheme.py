from typing import Any, Final

import pytest
from typing_extensions import override

from dmr.controller import Controller
from dmr.endpoint import Endpoint
from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators.security_scheme import (
    SecuritySchemeGenerator,
)
from dmr.openapi.objects.components import Components
from dmr.openapi.objects.security_requirement import (
    SecurityRequirement,
)
from dmr.openapi.objects.security_scheme import SecurityScheme
from dmr.security import SyncAuth
from dmr.serializer import BaseSerializer

_TEST_CONFIG: Final = OpenAPIConfig(title='Test API', version='1.0.0')


class _NoSchemeAuth(SyncAuth):
    @override
    def __call__(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
    ) -> Any | None:
        raise NotImplementedError

    @property
    @override
    def security_scheme(self) -> Components:
        return Components()

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
    ) -> Any | None:
        raise NotImplementedError

    @property
    @override
    def security_scheme(self) -> Components:
        return Components(
            security_schemes={
                'testScheme': SecurityScheme(type='http', scheme='bearer'),
            },
        )

    @property
    @override
    def security_requirement(self) -> SecurityRequirement:
        return {'testScheme': []}


@pytest.fixture
def context() -> OpenAPIContext:
    """Create ``OpenAPIContext`` instance for testing."""
    return OpenAPIContext(config=_TEST_CONFIG)


@pytest.fixture
def generator(context: OpenAPIContext) -> SecuritySchemeGenerator:
    """Create ``SecuritySchemeGenerator`` instance for testing."""
    return context.generators.security_scheme


def test_security_scheme_generator_no_schemes(
    generator: SecuritySchemeGenerator,
) -> None:
    """Ensure that auth providers without schemes are handled."""
    auth = _NoSchemeAuth()
    requirements = generator([auth])

    assert requirements == [{'noScheme': []}]
    assert len(generator._context.registries.security_scheme.schemes) == 0


def test_security_scheme_generator_with_schemes(
    generator: SecuritySchemeGenerator,
) -> None:
    """Ensure that auth providers with schemes are handled."""
    auth = _WithSchemeAuth()
    requirements = generator([auth])

    assert requirements == [{'testScheme': []}]
    assert 'testScheme' in generator._context.registries.security_scheme.schemes
