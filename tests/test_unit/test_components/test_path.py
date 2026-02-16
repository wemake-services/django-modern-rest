from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse
from django.test import RequestFactory

from django_modern_rest import Controller, Path
from django_modern_rest.plugins.pydantic import PydanticSerializer


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


def test_path_unnamed_parameters_raises(rf: RequestFactory) -> None:
    """Ensure that unnamed path parameters (args) are not allowed."""
    request = rf.get('/users/1')

    # Simulate calling the view with unnamed path parameter '1'
    response = _PathController.as_view()(request, '1')

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers['Content-Type'] == 'application/json'
