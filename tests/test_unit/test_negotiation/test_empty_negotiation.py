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
def _setup_parser_and_renderer(settings: LazySettings) -> Iterator[None]:
    clear_settings_cache()

    settings.DMR_SETTINGS = {
        Settings.parser_types: [],
        Settings.renderer_types: [],
    }

    yield

    clear_settings_cache()


def test_empty_parser_type() -> None:
    """Ensure that always has to be at least one parser type."""
    with pytest.raises(EndpointMetadataError, match='parser type'):

        class _Controller(Controller[PydanticSerializer]):
            renderer_types = [JsonRenderer]

            def post(self) -> dict[str, str]:
                raise NotImplementedError


def test_empty_renderer_type() -> None:
    """Ensure that always has to be at least one renderer type."""
    with pytest.raises(EndpointMetadataError, match='renderer type'):

        class _Controller(Controller[PydanticSerializer]):
            parser_types = [JsonParser]

            def post(self) -> dict[str, str]:
                raise NotImplementedError
