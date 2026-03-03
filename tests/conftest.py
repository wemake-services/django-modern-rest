import pytest

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext


@pytest.fixture
def openapi_context() -> OpenAPIContext:
    """Returns OpenAPI context for the spec tests."""
    return OpenAPIContext(OpenAPIConfig(title='tests', version='0.0.1'))
