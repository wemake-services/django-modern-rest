from http import HTTPMethod, HTTPStatus
from types import MappingProxyType
from typing import Final

import pytest
import yaml
from django.conf import LazySettings
from django.urls import reverse

from dmr.settings import Settings
from dmr.test import DMRClient


@pytest.fixture(params=[True, False], name='use_cdn')
def use_cdn(request: pytest.FixtureRequest) -> bool:
    """Run integration tests with both local static files and CDN URLs."""
    return bool(request.param)


@pytest.fixture(autouse=True, params=[True, False])
def _modify_cdn_settings(
    settings: LazySettings,
    request: pytest.FixtureRequest,
    *,
    use_cdn: bool,
) -> None:
    if not use_cdn:
        return

    settings.DMR_SETTINGS = {
        Settings.openapi_static_cdn: {
            'swagger': ('https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.1'),
            'redoc': (
                'https://cdn.redoc.ly/redoc/2.5.2/bundles/redoc.standalone.js'
            ),
            'scalar': (
                'https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.49.2/dist/browser/standalone.js'
            ),
            'stoplight': 'https://unpkg.com/@stoplight/elements@9.0.16',
        },
    }


_ENDPOINTS: Final = MappingProxyType({
    'openapi_json': 'application/json',
    'openapi_yaml': 'application/yaml',
    'stoplight': 'text/html',
    'swagger': 'text/html',
    'scalar': 'text/html',
    'redoc': 'text/html',
})


@pytest.mark.parametrize(
    ('endpoint_name', 'expected_content_type'),
    _ENDPOINTS.items(),
)
def test_endpoints(
    dmr_client: DMRClient,
    *,
    endpoint_name: str,
    expected_content_type: str,
) -> None:
    """Ensure that endpoints work."""
    response = dmr_client.get(reverse(endpoint_name))

    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == expected_content_type


@pytest.mark.parametrize(
    'endpoint_name',
    _ENDPOINTS.keys(),
)
@pytest.mark.parametrize(
    'method_name',
    [
        HTTPMethod.POST,
        HTTPMethod.PUT,
        HTTPMethod.PATCH,
        HTTPMethod.DELETE,
    ],
)
def test_wrong_method(
    dmr_client: DMRClient,
    *,
    endpoint_name: str,
    method_name: str,
) -> None:
    """Ensure that wrong HTTP method is correctly handled."""
    response = dmr_client.generic(method_name, reverse(endpoint_name))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_json_returns_correct_structure(dmr_client: DMRClient) -> None:
    """Ensure that OpenAPI JSON endpoint returns correct structure."""
    response = dmr_client.get(reverse('openapi_json'))

    assert response.headers['Content-Type'] == 'application/json'
    assert response.json()['openapi'] == '3.1.0'


def test_yaml_returns_correct_structure(dmr_client: DMRClient) -> None:
    """Ensure that OpenAPI YAML endpoint returns correct structure."""
    response = dmr_client.get(reverse('openapi_yaml'))

    assert response.headers['Content-Type'] == 'application/yaml'
    assert yaml.safe_load(response.content)['openapi'] == '3.1.0'
