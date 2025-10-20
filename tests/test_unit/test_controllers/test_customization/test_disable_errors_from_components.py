import json
from http import HTTPMethod, HTTPStatus
from typing import final

import pytest
from django.http import HttpResponse

from django_modern_rest import Controller, ResponseDescription, modify, validate
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


@final
class _WrongController(Controller[PydanticSerializer]):
    """All return types of these methods are not correct."""

    responses_from_components = False

    def get(self) -> str:
        return 1  # type: ignore[return-value]

    @modify(status_code=HTTPStatus.OK)
    def post(self) -> int:
        return 'missing'  # type: ignore[return-value]

    @validate(
        ResponseDescription(
            return_type=dict[str, int],
            status_code=HTTPStatus.OK,
        ),
    )
    def patch(self) -> HttpResponse:
        return HttpResponse(b'[]')


@pytest.mark.parametrize(
    'method',
    [
        HTTPMethod.GET,
        HTTPMethod.POST,
        HTTPMethod.PATCH,
    ],
)
def test_responses_are_not_added(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures that response validation works for default settings."""
    endpoint = _WrongController.api_endpoints[str(method).lower()]
    assert len(endpoint.metadata.responses) == 1

    request = dmr_rf.generic(str(method), '/whatever/')

    response = _WrongController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert json.loads(response.content)['detail']
