from http import HTTPStatus
from typing import Any, final

import pydantic
import pytest
from django.http import HttpResponse

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _ReturnModel(pydantic.BaseModel):
    full_name: str

    model_config = pydantic.ConfigDict(extra='forbid')


@final
class _ModelConfigController(
    Controller[PydanticSerializer],
    Body[_ReturnModel],
):
    def post(self) -> _ReturnModel:
        return self.parsed_body


@pytest.mark.parametrize(
    ('request_data', 'status_code'),
    [
        ({'full_name': ''}, HTTPStatus.CREATED),
        ({'full_name': '', 'extra': ''}, HTTPStatus.BAD_REQUEST),
    ],
)
def test_model_config_respected(
    dmr_rf: DMRRequestFactory,
    *,
    request_data: Any,
    status_code: HTTPStatus,
) -> None:
    """Ensures by default forward refs are working."""
    request = dmr_rf.post('/whatever/', data=request_data)

    response = _ModelConfigController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status_code
