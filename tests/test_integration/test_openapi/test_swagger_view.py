from http import HTTPStatus
from typing import Final

import pytest
from django.urls import reverse

from django_modern_rest.test import DMRClient

_REVERSE_NAME: Final = 'openapi:swagger'


@pytest.mark.parametrize(
    ('endpoint_name', 'expected_status', 'expected_content_type'),
    [
        (_REVERSE_NAME, HTTPStatus.OK, 'text/html'),
    ],
)
def test_endpoints(
    dmr_client: DMRClient,
    *,
    endpoint_name: str,
    expected_status: int,
    expected_content_type: str,
) -> None:
    """Ensure that endpoints work."""
    url = reverse(endpoint_name)
    response = dmr_client.get(url)

    assert response.status_code == expected_status
    assert response.headers['Content-Type'] == expected_content_type


@pytest.mark.parametrize(
    ('endpoint_name', 'expected_status'),
    [
        (_REVERSE_NAME, HTTPStatus.METHOD_NOT_ALLOWED),
    ],
)
def test_wrong_method(
    dmr_client: DMRClient,
    *,
    endpoint_name: str,
    expected_status: int,
) -> None:
    """Ensure that wrong HTTP method is correctly handled."""
    url = reverse(endpoint_name)
    response = dmr_client.post(url)

    assert response.status_code == expected_status
