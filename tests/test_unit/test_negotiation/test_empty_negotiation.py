import pytest
from django.conf import LazySettings

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.parsers import JsonParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import JsonRenderer
from dmr.settings import Settings


def test_empty_parsers(
    dmr_settings: LazySettings,
) -> None:
    """Ensure that always has to be at least one parser type."""
    dmr_settings.DMR_SETTINGS = {
        Settings.parsers: [],
        Settings.renderers: [JsonRenderer()],
    }

    with pytest.raises(EndpointMetadataError, match='at least one parser'):

        class _Controller(Controller[PydanticSerializer]):
            def post(self) -> dict[str, str]:
                raise NotImplementedError


def test_empty_renderers(
    dmr_settings: LazySettings,
) -> None:
    """Ensure that always has to be at least one renderer type."""
    dmr_settings.DMR_SETTINGS = {
        Settings.parsers: [JsonParser()],
        Settings.renderers: [],
    }

    with pytest.raises(EndpointMetadataError, match='at least one renderer'):

        class _Controller(Controller[PydanticSerializer]):
            def post(self) -> dict[str, str]:
                raise NotImplementedError
