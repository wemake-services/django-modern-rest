import pytest
from django.conf import LazySettings

from dmr.settings import Settings


@pytest.fixture(autouse=True)
def _generate_examples(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    # Our own settings:
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 1}
