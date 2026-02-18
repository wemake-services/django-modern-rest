from http import HTTPStatus
from typing import cast

from django.http import HttpResponse

from dmr import (
    Controller,
    ResponseSpec,
    validate,
)
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


class _QueryController(Controller[PydanticSerializer]):
    allowed_http_methods = frozenset((
        *Controller.allowed_http_methods,
        'query',
    ))

    @validate(
        ResponseSpec(None, status_code=HTTPStatus.OK),
    )
    def query(self) -> HttpResponse:
        return self.to_response(None, status_code=HTTPStatus.OK)


def test_query_method(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that `query` method is supported."""
    request = dmr_rf.generic('query', '/whatever/')

    response = cast(HttpResponse, _QueryController.as_view()(request))

    assert response.status_code == HTTPStatus.OK
    assert response.content == b''
