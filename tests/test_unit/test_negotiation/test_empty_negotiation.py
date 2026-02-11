import pytest
from django.conf import LazySettings

from django_modern_rest import (
    Controller,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.parsers import JsonParser
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.renderers import JsonRenderer
from django_modern_rest.settings import Settings


def test_empty_parser_type(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    """Ensure that always has to be at least one parser type."""
    settings.DMR_SETTINGS = {
        Settings.parsers: [],
        Settings.renderers: [JsonRenderer],
    }

    with pytest.raises(EndpointMetadataError, match='at least one parser'):

        class _Controller(Controller[PydanticSerializer]):
            def post(self) -> dict[str, str]:
                raise NotImplementedError


def test_empty_renderer_type(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    """Ensure that always has to be at least one renderer type."""
    settings.DMR_SETTINGS = {
        Settings.parsers: [JsonParser()],
        Settings.renderers: [],
    }

    with pytest.raises(EndpointMetadataError, match='at least one renderer'):

        class _Controller(Controller[PydanticSerializer]):
            def post(self) -> dict[str, str]:
                raise NotImplementedError
