import json
from collections.abc import Iterator
from http import HTTPMethod, HTTPStatus
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


@final
class _GlobalResponsesController(Controller[PydanticSerializer]):
    def post(self) -> int:
        raise APIError(1, status_code=HTTPStatus.PAYMENT_REQUIRED)


@pytest.mark.parametrize('method', [HTTPMethod.POST])
def test_global_responses(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.generic(str(method), '/whatever/')

    response = _GlobalResponsesController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert json.loads(response.content) == 1
