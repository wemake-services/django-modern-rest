from http import HTTPStatus
from typing import Final

import pytest
from django.urls import reverse

from dmr.openapi.objects.openapi import _OPENAPI_VERSION
from dmr.test import DMRClient

_ENDPOINTS: Final = (
    ('openapi:json', HTTPStatus.OK, 'application/json'),
    ('openapi:redoc', HTTPStatus.OK, 'text/html'),
    ('openapi:swagger', HTTPStatus.OK, 'text/html'),
    ('openapi:scalar', HTTPStatus.OK, 'text/html'),
)


@pytest.mark.parametrize(
    ('endpoint_name', 'expected_status', 'expected_content_type'),
    _ENDPOINTS,
)
def test_endpoints(
    dmr_client: DMRClient,
    *,
    endpoint_name: str,
    expected_status: int,
    expected_content_type: str,
) -> None:
    """Ensure that endpoints work."""
    response = dmr_client.get(reverse(endpoint_name))

    assert response.status_code == expected_status
    assert response.headers['Content-Type'] == expected_content_type


@pytest.mark.parametrize(
    ('endpoint_name', 'expected_status'),
    [(endpoint[0], HTTPStatus.METHOD_NOT_ALLOWED) for endpoint in _ENDPOINTS],
)
def test_wrong_method(
    dmr_client: DMRClient,
    *,
    endpoint_name: str,
    expected_status: int,
) -> None:
    """Ensure that wrong HTTP method is correctly handled."""
    response = dmr_client.post(reverse(endpoint_name))

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    'endpoint_name',
    ['openapi:json'],
)
def test_returns_correct_structure(
    dmr_client: DMRClient,
    *,
    endpoint_name: str,
) -> None:
    """Ensure that OpenAPI JSON endpoint returns correct structure."""
    response = dmr_client.get(reverse(endpoint_name))

    assert response.json()['openapi'] == _OPENAPI_VERSION
