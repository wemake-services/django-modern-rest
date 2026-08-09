import pathlib
from collections.abc import Callable, Iterator

import pytest
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.utils import translation

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext

# This import is required to always clean the settings cache:
from dmr_pytest import settings  # noqa: F401


@pytest.fixture
def openapi_context() -> OpenAPIContext:
    """Returns OpenAPI context for the spec tests."""
    return OpenAPIContext(OpenAPIConfig(title='tests', version='0.0.1'))


@pytest.fixture
def reset_language() -> Iterator[None]:
    """Deactivate the i18n after the request."""
    yield
    translation.deactivate()


@pytest.fixture
def fill_csrf() -> Callable[[HttpRequest], HttpRequest]:
    """Fill CSRF parameters for the prepared request."""

    def factory(request: HttpRequest) -> HttpRequest:
        csrf_token = get_token(request)
        request.META['HTTP_X_CSRFTOKEN'] = csrf_token
        request.COOKIES['csrftoken'] = csrf_token
        return request

    return factory


@pytest.fixture
def named_text_fixture() -> Callable[[str], str]:
    """Return an absolute file path to the fixture file."""

    def factory(fixture_name: str) -> str:
        return (
            pathlib.Path(__file__).parent / 'fixtures' / fixture_name
        ).read_text()

    return factory
