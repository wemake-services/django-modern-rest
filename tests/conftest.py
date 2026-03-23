from collections.abc import Iterator

import pytest
from django.utils import translation

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext

pytest_plugins = ['tracecov.pytest_plugin']


@pytest.fixture
def openapi_context() -> OpenAPIContext:
    """Returns OpenAPI context for the spec tests."""
    return OpenAPIContext(OpenAPIConfig(title='tests', version='0.0.1'))


@pytest.fixture
def reset_language() -> Iterator[None]:
    """Deactivate the i18n after the request."""
    yield
    translation.deactivate()
