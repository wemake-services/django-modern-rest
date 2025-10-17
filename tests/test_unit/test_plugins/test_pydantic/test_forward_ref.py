import json
from http import HTTPStatus
from typing import final

import pydantic
from django.http import HttpResponse

from django_modern_rest import Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _ReturnModel(pydantic.BaseModel):
    full_name: str


@final
class _ForwardRefController(Controller[PydanticSerializer]):
    def get(self) -> '_ReturnModel':
        return _ReturnModel(full_name='Example')


def test_forward_ref_pydantic(dmr_rf: DMRRequestFactory) -> None:
    """Ensures by default forward refs are working."""
    request = dmr_rf.get('/whatever/')

    response = _ForwardRefController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == {'full_name': 'Example'}
