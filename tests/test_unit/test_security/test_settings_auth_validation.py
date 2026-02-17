import pytest
from django.conf import LazySettings

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory


def test_settings_auth_none(
    settings: LazySettings,
    dmr_rf: DMRRequestFactory,
    dmr_clean_settings: None,
) -> None:
    """Ensures you can't set `Settings.auth` to `None`."""
    settings.DMR_SETTINGS = {
        Settings.auth: None,
    }

    with pytest.raises(EndpointMetadataError, match=r'Settings\.auth'):

        class _Controller(Controller[PydanticSerializer]):
            def get(self) -> str:
                raise NotImplementedError
