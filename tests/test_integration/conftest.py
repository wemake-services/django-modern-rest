import pytest
import tracecov
from django.conf import LazySettings

from dmr.settings import Settings


@pytest.fixture(scope='session')
def tracecov_map() -> tracecov.CoverageMap:
    """Provide the session ``tracecov`` coverage map for tests."""
    from django_test_app.server.urls import schema  # noqa: PLC0415

    return tracecov.CoverageMap.from_dict(schema.convert())


@pytest.fixture(autouse=True, params=[True, False])
def _modify_integration_settings(
    dmr_settings: LazySettings,
    request: pytest.FixtureRequest,
) -> None:
    # Django common settings:
    dmr_settings.DEBUG = request.param  # We run tests in both modes.
    # Our own settings:
    dmr_settings.DMR_SETTINGS = {
        Settings.openapi_examples_seed: 1,
        # It might be already defined in some other place:
        **getattr(dmr_settings, 'DMR_SETTINGS', {}),
    }
