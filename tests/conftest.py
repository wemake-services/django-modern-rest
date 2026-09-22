import contextlib
import inspect
import pathlib
from collections.abc import Callable, Iterator

import freezegun
import pytest
from django.conf import LazySettings
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.utils import translation

from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext

# This import is required to always clean the settings cache:
from dmr_pytest import settings  # noqa: F401

# `freezegun` inspects all attributes of all imported modules
# to find `datetime` and `time` objects to patch.
freezegun.configure(extend_ignore_list=['testcontainers', 'docker'])


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
def fill_csrf(
    settings: LazySettings,  # noqa: F811
) -> Callable[[HttpRequest], HttpRequest]:
    """Fill CSRF parameters for the prepared request."""

    def factory(request: HttpRequest) -> HttpRequest:
        csrf_token = get_token(request)
        request.META[settings.CSRF_HEADER_NAME] = csrf_token
        request.COOKIES[settings.CSRF_COOKIE_NAME] = csrf_token
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


@pytest.fixture(autouse=True)
def _close_async_db_connections(
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    """
    Close database connections left behind by async tests.

    Django's async ORM executes queries via ``sync_to_async``,
    which runs them on a process-wide worker thread
    (``asgiref.sync.SyncToAsync.single_thread_executor``).
    That thread keeps its own copy of ``django.db.connections``,
    which pytest-django never closes,
    because its teardown only sees the main thread's connections.
    The leftover session locks the test database,
    so the worker cannot drop it during session teardown
    (``ObjectInUse``: database is being accessed by other users).
    """
    yield

    func = getattr(request.node, 'function', None)
    if func is None or not inspect.iscoroutinefunction(func):
        return
    from asgiref.sync import SyncToAsync  # noqa: PLC0415
    from django.db import connections  # noqa: PLC0415

    future = SyncToAsync.single_thread_executor.submit(connections.close_all)
    with contextlib.suppress(Exception):
        future.result()
