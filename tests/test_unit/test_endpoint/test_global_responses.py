import json
from http import HTTPStatus
from typing import final

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot

from django_modern_rest import (
    APIError,
    Controller,
    ResponseSpec,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@pytest.fixture(autouse=True)
def _set_global_responses(
    settings: LazySettings,
    dmr_clean_settings: None,
) -> None:
    settings.DMR_SETTINGS = {
        'responses': [
            ResponseSpec(int, status_code=HTTPStatus.PAYMENT_REQUIRED),
        ],
    }


def test_global_responses(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that response status_code validation works."""
    request = dmr_rf.post('/whatever/')

    class _GlobalResponsesController(Controller[PydanticSerializer]):
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
    assert json.loads(response.content) == snapshot({
        'detail': [
            {
                'msg': (
                    'Returned status code 401 is not specified '
                    'in the list of allowed status codes: [201, 422, 406]'
                ),
                'type': 'value_error',
            },
        ],
    })


def test_global_responses_implicit_validate(dmr_rf: DMRRequestFactory) -> None:
    """Ensures that response can work with implicit `@validate`."""
    request = dmr_rf.post('/whatever/')

    class _GlobalResponsesController(Controller[PydanticSerializer]):
        def post(self) -> HttpResponse:
            return self.to_response(1, status_code=HTTPStatus.PAYMENT_REQUIRED)

    response = _GlobalResponsesController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.PAYMENT_REQUIRED, response.content
    assert json.loads(response.content) == 1
