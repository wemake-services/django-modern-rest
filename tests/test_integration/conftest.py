import pytest
import tracecov
from django.conf import LazySettings
from tracecov.pytest_plugin import _TRACECOV_MAP_KEY

from dmr.settings import Settings
from dmr.test import DMRClient


@pytest.fixture(scope='session')
def tracecov_map(pytestconfig: pytest.Config) -> tracecov.CoverageMap:
    """Provide the session ``tracecov`` coverage map for tests."""
    from django_test_app.server.urls import schema  # noqa: PLC0415

    coverage_map = tracecov.CoverageMap.from_dict(schema.convert())

    # TraceCov uses an autouse *session* bridge to stash the map.
    # In unit-test runs `tracecov_map` becomes `None`, so the bridge
    # never stores anything in `pytestconfig.stash`. Later integration
    # fixtures can't retroactively fix the stash, so the plugin sees
    # `None` and skips report generation.
    pytestconfig.stash[_TRACECOV_MAP_KEY] = coverage_map
    return coverage_map


@pytest.fixture
def dmr_client(
    dmr_client: DMRClient,
    tracecov_map: tracecov.CoverageMap,
) -> DMRClient:
    """
    Override the ``dmr_client`` fixture for integration tests.

    This replaces the base fixture so that integration tests record
    interaction in ``tracecov_map``. As a result, these requests are included
    in the TraceCov report.
    """
    tracecov_map.django.track_client(dmr_client)
    return dmr_client


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
