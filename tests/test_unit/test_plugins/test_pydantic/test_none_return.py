from http import HTTPStatus
from typing import final

from django.http import HttpResponse

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


@final
class _NoneReturnController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self) -> None:
        """Does not return anything."""


def test_pydantic_none_return(
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensures that `None` works as the return model."""
    request = dmr_rf.post('/whatever/', data={})

    response = _NoneReturnController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b''
