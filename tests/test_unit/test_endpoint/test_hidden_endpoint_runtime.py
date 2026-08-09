import json
from http import HTTPMethod, HTTPStatus
from typing import Final

import pytest
from django.http import HttpResponse

from dmr import Controller, ResponseSpec, modify, validate
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.test import DMRRequestFactory

_RESPONSE_DATA: Final = 'response data'


class _PartiallyHiddenController(Controller[PydanticFastSerializer]):
    # Will not be hidden:

    @modify(status_code=HTTPStatus.OK)
    def post(self) -> str:
        return _RESPONSE_DATA

    def get(self) -> str:
        return _RESPONSE_DATA

    @validate(ResponseSpec(str, status_code=HTTPStatus.OK))
    def delete(self) -> HttpResponse:
        return self.to_response(_RESPONSE_DATA)

    # Will be hidden:

    @modify(ignore_from_spec=True)
    def put(self) -> str:
        return _RESPONSE_DATA

    @validate(
        ResponseSpec(str, status_code=HTTPStatus.OK),
        ignore_from_spec=True,
    )
    def patch(self) -> HttpResponse:
        return self.to_response(_RESPONSE_DATA)


@pytest.mark.parametrize(
    ('method', 'hidden'),
    [
        (HTTPMethod.POST, False),
        (HTTPMethod.GET, False),
        (HTTPMethod.DELETE, False),
        (HTTPMethod.PUT, True),
        (HTTPMethod.PATCH, True),
    ],
)
def test_hidden_endpoints(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
    hidden: bool,
) -> None:
    """Ensures that hidden endpoints work correctly."""
    endpoint = _PartiallyHiddenController.api_endpoints[str(method)]
    assert endpoint.metadata.ignore_from_spec is hidden

    request = dmr_rf.generic(str(method).lower(), '/')
    response = _PartiallyHiddenController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert json.loads(response.content) == _RESPONSE_DATA
