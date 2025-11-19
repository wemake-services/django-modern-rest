from typing import Any
from unittest.mock import Mock

import pytest

from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.openapi import OpenAPIConfig
from django_modern_rest.openapi.core.context import OpenAPIContext
from django_modern_rest.openapi.generators.operation import OperationGenerator


@pytest.fixture
def generator() -> OperationGenerator:
    """Creates OperationGenerator."""
    config = OpenAPIConfig(title='Test', version='1.0.0')
    context = OpenAPIContext(config)
    return OperationGenerator(context)


@pytest.mark.parametrize(
    ('method', 'component_parsers'),
    [
        ('POST', [(Mock, ())]),  # Empty tuple for type_args
        ('GET', []),  # No component parsers
    ],
)
def test_generate_with_empty_responses(
    generator: OperationGenerator,
    *,
    method: str,
    component_parsers: list[Any],
) -> None:
    """Ensure generate returns None when metadata is minimal."""
    endpoint = Mock()
    endpoint.metadata = EndpointMetadata(
        responses={},
        validate_responses=False,
        method=method,
        modification=None,
        error_handler=None,
        component_parsers=component_parsers,
    )

    operation = generator.generate(endpoint)

    assert operation is not None
    assert operation.request_body is None
    assert operation.responses is None
