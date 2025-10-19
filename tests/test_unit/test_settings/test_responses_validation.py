from collections.abc import Iterator
from http import HTTPStatus

import pytest
from django.conf import LazySettings

from django_modern_rest import (
    ResponseDescription,
)
from django_modern_rest.exceptions import EndpointMetadataError
from django_modern_rest.settings import clear_settings_cache, resolve_responses


@pytest.fixture(autouse=True)
def _clear_cache(settings: LazySettings) -> Iterator[None]:
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_duplicate_global_responses(settings: LazySettings) -> None:
    """Ensures that duplicate global responses are validated."""
    settings.DMR_SETTINGS = {
        'responses': [
            ResponseDescription(int, status_code=HTTPStatus.PAYMENT_REQUIRED),
            ResponseDescription(str, status_code=HTTPStatus.PAYMENT_REQUIRED),
        ],
    }

    with pytest.raises(EndpointMetadataError, match='responses'):
        resolve_responses()


def test_no_content_global_responses(settings: LazySettings) -> None:
    """Ensures that base http spec with global responses is validated."""
    settings.DMR_SETTINGS = {
        'responses': [
            ResponseDescription(int, status_code=HTTPStatus.NO_CONTENT),
        ],
    }

    with pytest.raises(EndpointMetadataError, match='responses'):
        resolve_responses()
