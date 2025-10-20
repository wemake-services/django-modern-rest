import json
from collections.abc import Iterator
from http import HTTPStatus
from typing import final

import pytest
from django.conf import LazySettings
from django.http import HttpResponse

from django_modern_rest import (
    APIError,
    Controller,
    ResponseDescription,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.settings import clear_settings_cache
from django_modern_rest.test import DMRRequestFactory


@pytest.fixture(autouse=True)
def _set_global_responses(settings: LazySettings) -> Iterator[None]:
    clear_settings_cache()
    settings.DMR_SETTINGS = {
        'responses': [
            ResponseDescription(int, status_code=HTTPStatus.PAYMENT_REQUIRED),
        ],
    }
    yield
    clear_settings_cache()


def test_global_responses(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.post('/whatever/')

    class _GlobalResponsesController(Controller[PydanticSerializer]):
        """Needs to be inside a test for fixture with responses to work."""

        def post(self) -> int:
            raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    response = _GlobalResponsesController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED, response.content
    assert json.loads(response.content) == 1


@final
class _WrongGlobalResponseController(Controller[PydanticSerializer]):
    def post(self) -> int:
        raise APIError('abc', status_code=HTTPStatus.UNAUTHORIZED)


def test_wrong_global_response(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.post('/whatever/')

    response = _WrongGlobalResponseController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert '401' in json.loads(response.content)['detail']
