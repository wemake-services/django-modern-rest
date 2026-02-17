from typing import Any, Final

import pytest
from typing_extensions import override

from django_modern_rest.controller import Controller
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.core.context import OpenAPIContext
from django_modern_rest.openapi.generators.security_scheme import (
    SecuritySchemeGenerator,
)
from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.openapi.objects.security_requirement import (
    SecurityRequirement,
)
from django_modern_rest.openapi.objects.security_scheme import SecurityScheme
from django_modern_rest.security import SyncAuth
from django_modern_rest.serializer import BaseSerializer

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
