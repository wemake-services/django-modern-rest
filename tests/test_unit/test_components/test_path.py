from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse

from dmr import Controller, Path
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _PathModel(pydantic.BaseModel):
    user_id: int


@final
class _PathController(
    Path[_PathModel],
    Controller[PydanticSerializer],
):
    def get(self) -> _PathModel:
        raise NotImplementedError


def test_path_unnamed_parameters_raises(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that unnamed path parameters (args) are not allowed."""
    request = dmr_rf.get('/users/1')

    # Simulate calling the view with unnamed path parameter '1'
    response = _PathController.as_view()(request, '1')

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers['Content-Type'] == 'application/json'
