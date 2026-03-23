from collections.abc import Iterator

import pytest
import tracecov
from django.utils import translation

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext

pytest_plugins = ['tracecov.pytest_plugin']


@pytest.fixture(scope='session')
def tracecov_map() -> tracecov.CoverageMap:
    """
    Provide the session ``tracecov`` coverage map for the whole test run.

    It is built from the `django-test-app` schema. Declared here so the
    ``tracecov`` pytest plugin can stash the same map for reports.
    Map defined only under ``test_integration`` would not reliably
    hook into that path.
    """
    from django_test_app.server.urls import schema  # noqa: PLC0415

    return tracecov.CoverageMap.from_dict(schema.convert())


@pytest.fixture
def openapi_context() -> OpenAPIContext:
    """Returns OpenAPI context for the spec tests."""
    return OpenAPIContext(OpenAPIConfig(title='tests', version='0.0.1'))


@pytest.fixture
def reset_language() -> Iterator[None]:
    """Deactivate the i18n after the request."""
    yield
    translation.deactivate()
