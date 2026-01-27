from collections.abc import Iterator

import pytest
from django.conf import LazySettings

from django_modern_rest import (
    Controller,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.parsers import JsonParser
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.renderers import JsonRenderer
from django_modern_rest.settings import (
    Settings,
    clear_settings_cache,
)


@pytest.fixture(autouse=True)
def _clear_settings() -> Iterator[None]:
    clear_settings_cache()

    yield

    clear_settings_cache()


def test_empty_parser_type(settings: LazySettings) -> None:
    """Ensure that always has to be at least one parser type."""
    settings.DMR_SETTINGS = {
        Settings.parsers: [],
        Settings.renderers: [JsonRenderer],
    }

    with pytest.raises(EndpointMetadataError, match='parser type'):

        class _Controller(Controller[PydanticSerializer]):
            def post(self) -> dict[str, str]:
                raise NotImplementedError


def test_empty_renderer_type(settings: LazySettings) -> None:
    """Ensure that always has to be at least one renderer type."""
    settings.DMR_SETTINGS = {
        Settings.parsers: [JsonParser],
        Settings.renderers: [],
    }

    with pytest.raises(EndpointMetadataError, match='renderer type'):

        class _Controller(Controller[PydanticSerializer]):
            def post(self) -> dict[str, str]:
                raise NotImplementedError
