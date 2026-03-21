import pytest
from django.conf import LazySettings

from dmr.settings import Settings


@pytest.fixture(autouse=True, params=[True, False], name='use_cdn')
def _use_cdn(request: pytest.FixtureRequest) -> bool:
    """Run integration tests with both local static files and CDN URLs."""
    return bool(request.param)


@pytest.fixture(autouse=True, params=[True, False])
def _modify_integration_settings(
    settings: LazySettings,
    request: pytest.FixtureRequest,
    dmr_clean_settings: None,
    *use_cdn: bool,
) -> None:
    # Django common settings:
    settings.DEBUG = request.param  # We run tests in both modes.
    # Our own settings:
    settings.DMR_SETTINGS = {
        Settings.openapi_examples_seed: 1,
        Settings.openapi_static_cdn: (
            {
                'swagger': (
                    'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.1'
                ),
                'redoc': (
                    'https://cdn.redoc.ly/redoc/2.5.2/bundles/redoc.standalone.js'
                ),
                'scalar': (
                    'https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.49.2/dist/browser/standalone.js'
                ),
            }
            if use_cdn
            else {}
        ),
    }
