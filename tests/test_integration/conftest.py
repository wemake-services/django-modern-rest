from typing import TYPE_CHECKING

import pytest
from django.conf import LazySettings

from dmr.settings import Settings

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


@pytest.fixture(autouse=True)
def _set_dmr_settings(settings: LazySettings) -> None:
    settings.DMR_SETTINGS = {
        Settings.openapi_examples_seed: 1,
        # It might be already defined in some other place:
        **getattr(settings, 'DMR_SETTINGS', {}),
    }


@pytest.fixture(autouse=True, params=[True, False])
def _modify_integration_settings(
    settings: LazySettings,
    request: pytest.FixtureRequest,
) -> None:
    settings.DEBUG = request.param  # We run tests in both modes.
