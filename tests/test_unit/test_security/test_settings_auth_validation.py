import pytest
from django.conf import LazySettings

from django_modern_rest import Controller
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.settings import Settings
from django_modern_rest.test import DMRRequestFactory


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
