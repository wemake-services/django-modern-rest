import pytest

from dmr.openapi import OpenAPIConfig


@pytest.mark.parametrize(
    'openapi_version',
    [
        '3.1.0',
        '3.1.1',
        '3.2.0',
        '4.0.0',
    ],
)
def test_supported_openapi_versions(openapi_version: str) -> None:
    """Ensures that ``3.1.0`` and newer versions are allowed."""
    config = OpenAPIConfig(
        title='my title',
        version='1.0.0',
        openapi_version=openapi_version,
    )

    assert config.openapi_version == openapi_version


@pytest.mark.parametrize(
    'openapi_version',
    [
        '3.0.0',
        '3.0.4',
        '2.0.0',
    ],
)
def test_unsupported_openapi_versions(openapi_version: str) -> None:
    """Ensures that versions older than ``3.1.0`` are rejected."""
    with pytest.raises(ValueError, match=r'versions before 3\.1\.0'):
        OpenAPIConfig(
            title='my title',
            version='1.0.0',
            openapi_version=openapi_version,
        )


@pytest.mark.parametrize(
    'openapi_version',
    [
        '3.2.0',
        '3.3.0',
        '4.0.0',
    ],
)
def test_self_uri_is_allowed(openapi_version: str) -> None:
    """Ensures that ``$self`` is allowed since OpenAPI ``3.2.0``."""
    config = OpenAPIConfig(
        title='my title',
        version='1.0.0',
        openapi_version=openapi_version,
        self_uri='https://example.com/openapi.json',
    )

    assert config.self_uri == 'https://example.com/openapi.json'


@pytest.mark.parametrize(
    'openapi_version',
    [
        '3.1.0',
        '3.1.1',
    ],
)
def test_self_uri_requires_openapi_v32(openapi_version: str) -> None:
    """Ensures that ``$self`` is rejected for versions without that field."""
    with pytest.raises(ValueError, match=r'`self_uri` requires OpenAPI 3\.2'):
        OpenAPIConfig(
            title='my title',
            version='1.0.0',
            openapi_version=openapi_version,
            self_uri='https://example.com/openapi.json',
        )
