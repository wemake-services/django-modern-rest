from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest
from django.conf import LazySettings

if TYPE_CHECKING:
    import tracecov


@pytest.fixture(scope='session')
def tracecov_map() -> 'tracecov.CoverageMap | None':
    """Provide the session ``tracecov`` coverage map for tests."""
    try:
        import tracecov  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        return None

    from django_test_app.server.urls import schema  # noqa: PLC0415

    return tracecov.CoverageMap.from_dict(schema.convert())


@pytest.fixture(autouse=True, scope='module')
def _openapi_schema_cache_clear() -> Iterator[None]:
    """
    Clear the cache on the OpenAPI instance that is used for tests.

    The converted schema does not depend on any setting that tests change:
    examples are generated when the schema is built on import, not converted.
    So we only clear the cache once per module, not after every test,
    since converting and validating the whole test app schema is slow.
    """
    from server.urls import schema  # type: ignore[import-not-found]  #  noqa: PLC0415

    yield
    schema.cache_clear()


@pytest.fixture(autouse=True, params=[True, False])
def _modify_integration_settings(
    settings: LazySettings,
    request: pytest.FixtureRequest,
) -> None:
    settings.DEBUG = request.param  # We run tests in both modes.
