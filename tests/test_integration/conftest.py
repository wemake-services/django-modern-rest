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
    settings: LazySettings,
    request: pytest.FixtureRequest,
    dmr_clean_settings: None,
) -> None:
    # Django common settings:
    settings.DEBUG = request.param  # We run tests in both modes.
    # Our own settings:
    settings.DMR_SETTINGS = {
        Settings.openapi_examples_seed: 1,
        # It might be already defined in some other place:
        **getattr(settings, 'DMR_SETTINGS', {}),
    }
