import json
from http import HTTPStatus

import pytest
from django.conf import LazySettings
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller, ResponseSpec, validate
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import Settings
from dmr.test import DMRRequestFactory


@pytest.fixture(autouse=True)
def _disable_semantic_responses(
    settings: LazySettings,
) -> None:
    settings.DMR_SETTINGS = {
        Settings.semantic_responses: False,
    }


def test_runtime_no_semantic_responses(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Runtime execution should succeed."""

    class _SimpleController(
        Controller[PydanticSerializer],
    ):
        def get(self) -> list[int]:
            return [1, 2]

    response = _SimpleController.as_view()(dmr_rf.get('/'))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot([1, 2])


def test_response_validation_still_works(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Response validation must still reject incorrect return types."""

    class _WrongReturnController(Controller[PydanticSerializer]):
        def get(self) -> list[int]:
            return ['a']  # type: ignore[list-item]

    request = dmr_rf.get('/whatever/')
    response = _WrongReturnController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content) == snapshot(
        {
            'detail': [
                {
                    'msg': 'Input should be a valid integer',
                    'loc': ['0'],
                    'type': 'value_error',
                },
            ],
        },
    )


def test_missing_status_code_still_raises(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Missing status code response should still error when validation on."""

    class _WrongStatusController(Controller[PydanticSerializer]):
        @validate(
            ResponseSpec(
                return_type=list[int],
                status_code=HTTPStatus.CREATED,
            ),
        )
        def get(self) -> HttpResponse:
            return HttpResponse(
                b'[]',
                status=HTTPStatus.OK,
                content_type='application/json',
            )

    request = dmr_rf.get('/whatever/')
    response = _WrongStatusController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    expected_msg = (
        'Returned status code 200 is not specified'
        ' in the list of allowed status codes: [201]'
    )
    assert json.loads(response.content) == snapshot(
        {
            'detail': [
                {
                    'msg': expected_msg,
                    'type': 'value_error',
                },
            ],
        },
    )
