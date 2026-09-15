import pytest

from dmr.openapi import OpenAPIConfig, build_schema
from dmr.routing import Router


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
    assert config.json_schema_dialect is None


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


def test_self_uri() -> None:
    """Ensures that ``$self`` is stored on the config."""
    config = OpenAPIConfig(
        title='my title',
        version='1.0.0',
        openapi_version='3.2.0',
        self_uri='https://example.com/openapi.json',
    )

    assert config.self_uri == 'https://example.com/openapi.json'
def test_json_schema_dialect() -> None:
    """Ensures that ``json_schema_dialect`` ends up in the schema."""
    dialect = 'https://json-schema.org/draft/2020-12/schema'
    config = OpenAPIConfig(
        title='my title',
        version='1.0.0',
        json_schema_dialect=dialect,
    )

    assert config.json_schema_dialect == dialect

    schema = build_schema(Router(), config=config).convert()
    assert schema['jsonSchemaDialect'] == dialect
